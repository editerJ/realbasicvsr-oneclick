# RealBasicVSR standalone - mmcv/mmengine/mmagic 없이 순수 torch로 동작
# 원본 코드: open-mmlab/mmagic (Apache-2.0) real_basicvsr_net.py, basicvsr_net.py
import argparse, os, time
from logging import WARNING
import numpy as np
import cv2
import torch
from torch import Tensor
import torch.nn as nn
import torch.nn.functional as F

def make_layer(basic_block, num_basic_block, **kwarg):
    return nn.Sequential(*[basic_block(**kwarg) for _ in range(num_basic_block)])

class ConvModule(nn.Module):
    """mmcv ConvModule 최소 호환 (conv + optional ReLU). 키 이름(conv/activate) 동일 유지."""
    def __init__(self, in_channels, out_channels, kernel_size, stride, padding,
                 norm_cfg=None, act_cfg=None):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride,
                              padding, bias=True)
        self.activate = nn.ReLU(inplace=True) if act_cfg is not None else None
    def forward(self, x):
        x = self.conv(x)
        if self.activate is not None:
            x = self.activate(x)
        return x

class ResidualBlockNoBN(nn.Module):
    def __init__(self, mid_channels=64, res_scale=1.0):
        super().__init__()
        self.res_scale = res_scale
        self.conv1 = nn.Conv2d(mid_channels, mid_channels, 3, 1, 1, bias=True)
        self.conv2 = nn.Conv2d(mid_channels, mid_channels, 3, 1, 1, bias=True)
        self.relu = nn.ReLU(inplace=True)
    def forward(self, x):
        identity = x
        out = self.conv2(self.relu(self.conv1(x)))
        return identity + out * self.res_scale

def flow_warp(x,
              flow,
              interpolation='bilinear',
              padding_mode='zeros',
              align_corners=True):
    """Warp an image or a feature map with optical flow.

    Args:
        x (Tensor): Tensor with size (n, c, h, w).
        flow (Tensor): Tensor with size (n, h, w, 2). The last dimension is
            a two-channel, denoting the width and height relative offsets.
            Note that the values are not normalized to [-1, 1].
        interpolation (str): Interpolation mode: 'nearest' or 'bilinear'.
            Default: 'bilinear'.
        padding_mode (str): Padding mode: 'zeros' or 'border' or 'reflection'.
            Default: 'zeros'.
        align_corners (bool): Whether align corners. Default: True.

    Returns:
        Tensor: Warped image or feature map.
    """
    if x.size()[-2:] != flow.size()[1:3]:
        raise ValueError(f'The spatial sizes of input ({x.size()[-2:]}) and '
                         f'flow ({flow.size()[1:3]}) are not the same.')
    _, _, h, w = x.size()
    # create mesh grid
    device = flow.device
    # torch.meshgrid has been modified in 1.10.0 (compatibility with previous
    # versions), and will be further modified in 1.12 (Breaking Change)
    if 'indexing' in torch.meshgrid.__code__.co_varnames:
        grid_y, grid_x = torch.meshgrid(
            torch.arange(0, h, device=device, dtype=x.dtype),
            torch.arange(0, w, device=device, dtype=x.dtype),
            indexing='ij')
    else:
        grid_y, grid_x = torch.meshgrid(
            torch.arange(0, h, device=device, dtype=x.dtype),
            torch.arange(0, w, device=device, dtype=x.dtype))
    grid = torch.stack((grid_x, grid_y), 2)  # h, w, 2
    grid.requires_grad = False

    grid_flow = grid + flow
    # scale grid_flow to [-1,1]
    grid_flow_x = 2.0 * grid_flow[:, :, :, 0] / max(w - 1, 1) - 1.0
    grid_flow_y = 2.0 * grid_flow[:, :, :, 1] / max(h - 1, 1) - 1.0
    grid_flow = torch.stack((grid_flow_x, grid_flow_y), dim=3)
    grid_flow = grid_flow.type(x.type())
    output = F.grid_sample(
        x,
        grid_flow,
        mode=interpolation,
        padding_mode=padding_mode,
        align_corners=align_corners)
    return output


class PixelShufflePack(nn.Module):
    """Pixel Shuffle upsample layer.

    Args:
        in_channels (int): Number of input channels.
        out_channels (int): Number of output channels.
        scale_factor (int): Upsample ratio.
        upsample_kernel (int): Kernel size of Conv layer to expand channels.

    Returns:
        Upsampled feature map.
    """

    def __init__(self, in_channels: int, out_channels: int, scale_factor: int,
                 upsample_kernel: int):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.scale_factor = scale_factor
        self.upsample_kernel = upsample_kernel
        self.upsample_conv = nn.Conv2d(
            self.in_channels,
            self.out_channels * scale_factor * scale_factor,
            self.upsample_kernel,
            padding=(self.upsample_kernel - 1) // 2)

    def forward(self, x: Tensor) -> Tensor:
        """Forward function for PixelShufflePack.

        Args:
            x (Tensor): Input tensor with shape (n, c, h, w).

        Returns:
            Tensor: Forward results.
        """
        x = self.upsample_conv(x)
        x = F.pixel_shuffle(x, self.scale_factor)
        return x


class BasicVSRNet(nn.Module):
    """BasicVSR network structure for video super-resolution.

    Support only x4 upsampling.

    Paper:
        BasicVSR: The Search for Essential Components in Video Super-Resolution
        and Beyond, CVPR, 2021

    Args:
        mid_channels (int): Channel number of the intermediate features.
            Default: 64.
        num_blocks (int): Number of residual blocks in each propagation branch.
            Default: 30.
        spynet_pretrained (str): Pre-trained model path of SPyNet.
            Default: None.
    """

    def __init__(self, mid_channels=64, num_blocks=30, spynet_pretrained=None):

        super().__init__()

        self.mid_channels = mid_channels

        # optical flow network for feature alignment
        self.spynet = SPyNet(pretrained=spynet_pretrained)

        # propagation branches
        self.backward_resblocks = ResidualBlocksWithInputConv(
            mid_channels + 3, mid_channels, num_blocks)
        self.forward_resblocks = ResidualBlocksWithInputConv(
            mid_channels + 3, mid_channels, num_blocks)

        # upsample
        self.fusion = nn.Conv2d(
            mid_channels * 2, mid_channels, 1, 1, 0, bias=True)
        self.upsample1 = PixelShufflePack(
            mid_channels, mid_channels, 2, upsample_kernel=3)
        self.upsample2 = PixelShufflePack(
            mid_channels, 64, 2, upsample_kernel=3)
        self.conv_hr = nn.Conv2d(64, 64, 3, 1, 1)
        self.conv_last = nn.Conv2d(64, 3, 3, 1, 1)
        self.img_upsample = nn.Upsample(
            scale_factor=4, mode='bilinear', align_corners=False)

        # activation function
        self.lrelu = nn.LeakyReLU(negative_slope=0.1, inplace=True)

        self._raised_warning = False

    def check_if_mirror_extended(self, lrs):
        """Check whether the input is a mirror-extended sequence.

        If mirror-extended, the i-th (i=0, ..., t-1) frame is equal to the
        (t-1-i)-th frame.

        Args:
            lrs (tensor): Input LR images with shape (n, t, c, h, w)
        """

        self.is_mirror_extended = False
        if lrs.size(1) % 2 == 0:
            lrs_1, lrs_2 = torch.chunk(lrs, 2, dim=1)
            if torch.norm(lrs_1 - lrs_2.flip(1)) == 0:
                self.is_mirror_extended = True

    def compute_flow(self, lrs):
        """Compute optical flow using SPyNet for feature warping.

        Note that if the input is an mirror-extended sequence, 'flows_forward'
        is not needed, since it is equal to 'flows_backward.flip(1)'.

        Args:
            lrs (tensor): Input LR images with shape (n, t, c, h, w)

        Return:
            tuple(Tensor): Optical flow. 'flows_forward' corresponds to the
                flows used for forward-time propagation (current to previous).
                'flows_backward' corresponds to the flows used for
                backward-time propagation (current to next).
        """

        n, t, c, h, w = lrs.size()
        lrs_1 = lrs[:, :-1, :, :, :].reshape(-1, c, h, w)
        lrs_2 = lrs[:, 1:, :, :, :].reshape(-1, c, h, w)

        flows_backward = self.spynet(lrs_1, lrs_2).view(n, t - 1, 2, h, w)

        if self.is_mirror_extended:  # flows_forward = flows_backward.flip(1)
            flows_forward = None
        else:
            flows_forward = self.spynet(lrs_2, lrs_1).view(n, t - 1, 2, h, w)

        return flows_forward, flows_backward

    def forward(self, lrs):
        """Forward function for BasicVSR.

        Args:
            lrs (Tensor): Input LR sequence with shape (n, t, c, h, w).

        Returns:
            Tensor: Output HR sequence with shape (n, t, c, 4h, 4w).
        """
        n, t, c, h, w = lrs.size()
        if (h < 64 or w < 64) and not self._raised_warning:
            print(
                f'{self.__class__.__name__} is designed for input '
                'larger than 64x64, but the resolution of current image '
                f'is {h}x{w}. We recommend you to check your input.',
                'current', WARNING)
            self._raised_warning = True

        # check whether the input is an extended sequence
        self.check_if_mirror_extended(lrs)

        # compute optical flow
        flows_forward, flows_backward = self.compute_flow(lrs)

        # backward-time propagation
        outputs = []
        feat_prop = lrs.new_zeros(n, self.mid_channels, h, w)
        for i in range(t - 1, -1, -1):
            if i < t - 1:  # no warping required for the last timestep
                flow = flows_backward[:, i, :, :, :]
                feat_prop = flow_warp(feat_prop, flow.permute(0, 2, 3, 1))

            feat_prop = torch.cat([lrs[:, i, :, :, :], feat_prop], dim=1)
            feat_prop = self.backward_resblocks(feat_prop)

            outputs.append(feat_prop)
        outputs = outputs[::-1]

        # forward-time propagation and upsampling
        feat_prop = torch.zeros_like(feat_prop)
        for i in range(0, t):
            lr_curr = lrs[:, i, :, :, :]
            if i > 0:  # no warping required for the first timestep
                if flows_forward is not None:
                    flow = flows_forward[:, i - 1, :, :, :]
                else:
                    flow = flows_backward[:, -i, :, :, :]
                feat_prop = flow_warp(feat_prop, flow.permute(0, 2, 3, 1))

            feat_prop = torch.cat([lr_curr, feat_prop], dim=1)
            feat_prop = self.forward_resblocks(feat_prop)

            # upsampling given the backward and forward features
            out = torch.cat([outputs[i], feat_prop], dim=1)
            out = self.lrelu(self.fusion(out))
            out = self.lrelu(self.upsample1(out))
            out = self.lrelu(self.upsample2(out))
            out = self.lrelu(self.conv_hr(out))
            out = self.conv_last(out)
            base = self.img_upsample(lr_curr)
            out += base
            outputs[i] = out

        return torch.stack(outputs, dim=1)


class ResidualBlocksWithInputConv(nn.Module):
    """Residual blocks with a convolution in front.

    Args:
        in_channels (int): Number of input channels of the first conv.
        out_channels (int): Number of channels of the residual blocks.
            Default: 64.
        num_blocks (int): Number of residual blocks. Default: 30.
    """

    def __init__(self, in_channels, out_channels=64, num_blocks=30):
        super().__init__()

        main = []

        # a convolution used to match the channels of the residual blocks
        main.append(nn.Conv2d(in_channels, out_channels, 3, 1, 1, bias=True))
        main.append(nn.LeakyReLU(negative_slope=0.1, inplace=True))

        # residual blocks
        main.append(
            make_layer(
                ResidualBlockNoBN, num_blocks, mid_channels=out_channels))

        self.main = nn.Sequential(*main)

    def forward(self, feat):
        """Forward function for ResidualBlocksWithInputConv.

        Args:
            feat (Tensor): Input feature with shape (n, in_channels, h, w)

        Returns:
            Tensor: Output feature with shape (n, out_channels, h, w)
        """
        return self.main(feat)


class SPyNet(nn.Module):
    """SPyNet network structure.

    The difference to the SPyNet in [tof.py] is that
        1. more SPyNetBasicModule is used in this version, and
        2. no batch normalization is used in this version.

    Paper:
        Optical Flow Estimation using a Spatial Pyramid Network, CVPR, 2017

    Args:
        pretrained (str): path for pre-trained SPyNet. Default: None.
    """

    def __init__(self, pretrained):
        super().__init__()

        self.basic_module = nn.ModuleList(
            [SPyNetBasicModule() for _ in range(6)])

        if isinstance(pretrained, str):
            sd = torch.hub.load_state_dict_from_url(pretrained, map_location='cpu')
            self.load_state_dict(sd, strict=True)
            print('spynet pretrained loaded')
        elif pretrained is not None:
            raise TypeError('[pretrained] should be str or None, '
                            f'but got {type(pretrained)}.')

        self.register_buffer(
            'mean',
            torch.Tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer(
            'std',
            torch.Tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def compute_flow(self, ref, supp):
        """Compute flow from ref to supp.

        Note that in this function, the images are already resized to a
        multiple of 32.

        Args:
            ref (Tensor): Reference image with shape of (n, 3, h, w).
            supp (Tensor): Supporting image with shape of (n, 3, h, w).

        Returns:
            Tensor: Estimated optical flow: (n, 2, h, w).
        """
        n, _, h, w = ref.size()

        # normalize the input images
        ref = [(ref - self.mean) / self.std]
        supp = [(supp - self.mean) / self.std]

        # generate downsampled frames
        for level in range(5):
            ref.append(
                F.avg_pool2d(
                    input=ref[-1],
                    kernel_size=2,
                    stride=2,
                    count_include_pad=False))
            supp.append(
                F.avg_pool2d(
                    input=supp[-1],
                    kernel_size=2,
                    stride=2,
                    count_include_pad=False))
        ref = ref[::-1]
        supp = supp[::-1]

        # flow computation
        flow = ref[0].new_zeros(n, 2, h // 32, w // 32)
        for level in range(len(ref)):
            if level == 0:
                flow_up = flow
            else:
                flow_up = F.interpolate(
                    input=flow,
                    scale_factor=2,
                    mode='bilinear',
                    align_corners=True) * 2.0

            # add the residue to the upsampled flow
            flow = flow_up + self.basic_module[level](
                torch.cat([
                    ref[level],
                    flow_warp(
                        supp[level],
                        flow_up.permute(0, 2, 3, 1),
                        padding_mode='border'), flow_up
                ], 1))

        return flow

    def forward(self, ref, supp):
        """Forward function of SPyNet.

        This function computes the optical flow from ref to supp.

        Args:
            ref (Tensor): Reference image with shape of (n, 3, h, w).
            supp (Tensor): Supporting image with shape of (n, 3, h, w).

        Returns:
            Tensor: Estimated optical flow: (n, 2, h, w).
        """

        # upsize to a multiple of 32
        h, w = ref.shape[2:4]
        w_up = w if (w % 32) == 0 else 32 * (w // 32 + 1)
        h_up = h if (h % 32) == 0 else 32 * (h // 32 + 1)
        ref = F.interpolate(
            input=ref, size=(h_up, w_up), mode='bilinear', align_corners=False)
        supp = F.interpolate(
            input=supp,
            size=(h_up, w_up),
            mode='bilinear',
            align_corners=False)

        # compute flow, and resize back to the original resolution
        flow = F.interpolate(
            input=self.compute_flow(ref, supp),
            size=(h, w),
            mode='bilinear',
            align_corners=False)

        # adjust the flow values
        flow[:, 0, :, :] *= float(w) / float(w_up)
        flow[:, 1, :, :] *= float(h) / float(h_up)

        return flow


class SPyNetBasicModule(nn.Module):
    """Basic Module for SPyNet.

    Paper:
        Optical Flow Estimation using a Spatial Pyramid Network, CVPR, 2017
    """

    def __init__(self):
        super().__init__()

        self.basic_module = nn.Sequential(
            ConvModule(
                in_channels=8,
                out_channels=32,
                kernel_size=7,
                stride=1,
                padding=3,
                norm_cfg=None,
                act_cfg=dict(type='ReLU')),
            ConvModule(
                in_channels=32,
                out_channels=64,
                kernel_size=7,
                stride=1,
                padding=3,
                norm_cfg=None,
                act_cfg=dict(type='ReLU')),
            ConvModule(
                in_channels=64,
                out_channels=32,
                kernel_size=7,
                stride=1,
                padding=3,
                norm_cfg=None,
                act_cfg=dict(type='ReLU')),
            ConvModule(
                in_channels=32,
                out_channels=16,
                kernel_size=7,
                stride=1,
                padding=3,
                norm_cfg=None,
                act_cfg=dict(type='ReLU')),
            ConvModule(
                in_channels=16,
                out_channels=2,
                kernel_size=7,
                stride=1,
                padding=3,
                norm_cfg=None,
                act_cfg=None))

    def forward(self, tensor_input):
        """
        Args:
            tensor_input (Tensor): Input tensor with shape (b, 8, h, w).
                8 channels contain:
                [reference image (3), neighbor image (3), initial flow (2)].

        Returns:
            Tensor: Refined flow with shape (b, 2, h, w)
        """
        return self.basic_module(tensor_input)


class RealBasicVSRNet(nn.Module):
    """RealBasicVSR network structure for real-world video super-resolution.

    Support only x4 upsampling.

    Paper:
        Investigating Tradeoffs in Real-World Video Super-Resolution, arXiv

    Args:
        mid_channels (int, optional): Channel number of the intermediate
            features. Default: 64.
        num_propagation_blocks (int, optional): Number of residual blocks in
            each propagation branch. Default: 20.
        num_cleaning_blocks (int, optional): Number of residual blocks in the
            image cleaning module. Default: 20.
        dynamic_refine_thres (int, optional): Stop cleaning the images when
            the residue is smaller than this value. Default: 255.
        spynet_pretrained (str, optional): Pre-trained model path of SPyNet.
            Default: None.
        is_fix_cleaning (bool, optional): Whether to fix the weights of
            the image cleaning module during training. Default: False.
        is_sequential_cleaning (bool, optional): Whether to clean the images
            sequentially. This is used to save GPU memory, but the speed is
            slightly slower. Default: False.
    """

    def __init__(self,
                 mid_channels=64,
                 num_propagation_blocks=20,
                 num_cleaning_blocks=20,
                 dynamic_refine_thres=255,
                 spynet_pretrained=None,
                 is_fix_cleaning=False,
                 is_sequential_cleaning=False):

        super().__init__()

        self.dynamic_refine_thres = dynamic_refine_thres / 255.
        self.is_sequential_cleaning = is_sequential_cleaning

        # image cleaning module
        self.image_cleaning = nn.Sequential(
            ResidualBlocksWithInputConv(3, mid_channels, num_cleaning_blocks),
            nn.Conv2d(mid_channels, 3, 3, 1, 1, bias=True),
        )

        if is_fix_cleaning:  # keep the weights of the cleaning module fixed
            self.image_cleaning.requires_grad_(False)

        # BasicVSR
        self.basicvsr = BasicVSRNet(mid_channels, num_propagation_blocks,
                                    spynet_pretrained)
        self.basicvsr.spynet.requires_grad_(False)

    def forward(self, lqs, return_lqs=False):
        """Forward function for BasicVSR++.

        Args:
            lqs (tensor): Input low quality (LQ) sequence with
                shape (n, t, c, h, w).
            return_lqs (bool): Whether to return LQ sequence. Default: False.

        Returns:
            Tensor: Output HR sequence.
        """
        n, t, c, h, w = lqs.size()

        for _ in range(0, 3):  # at most 3 cleaning, determined empirically
            if self.is_sequential_cleaning:
                residues = []
                for i in range(0, t):
                    residue_i = self.image_cleaning(lqs[:, i, :, :, :])
                    lqs[:, i, :, :, :] += residue_i
                    residues.append(residue_i)
                residues = torch.stack(residues, dim=1)
            else:  # time -> batch, then apply cleaning at once
                lqs = lqs.view(-1, c, h, w)
                residues = self.image_cleaning(lqs)
                lqs = (lqs + residues).view(n, t, c, h, w)

            # determine whether to continue cleaning
            if torch.mean(torch.abs(residues)) < self.dynamic_refine_thres:
                break

        # Super-resolution (BasicVSR)
        outputs = self.basicvsr(lqs)

        if return_lqs:
            return outputs, lqs
        else:
            return outputs


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input')
    p.add_argument('--output', help='output dir for PNG frames')
    p.add_argument('--video', help='output mp4 path (no audio)')
    p.add_argument('--checkpoint', default='realbasicvsr_c64b20_1x30x8_lr5e-5_150k_reds_20211104-52f77c2c.pth')
    p.add_argument('--max-seq-len', type=int, default=40,
                   help='Frames per chunk (RTX 4070 8GB default 40). OOM이면 절반으로.')
    p.add_argument('--selftest', action='store_true')
    args = p.parse_args()

    SPYNET_URL = ('https://download.openmmlab.com/mmediting/restorers/'
                  'basicvsr/spynet_20210409-c6c1bd09.pth')

    if args.selftest:
        print('python ok')
        print('torch', torch.__version__, '| cuda:', torch.cuda.is_available())
        print('cv2', cv2.__version__, '| numpy', np.__version__)
        model = RealBasicVSRNet(
            mid_channels=64, num_propagation_blocks=20, num_cleaning_blocks=20,
            dynamic_refine_thres=255, spynet_pretrained=SPYNET_URL)
        ckpt = torch.load(args.checkpoint, map_location='cpu', weights_only=False)
        sd = ckpt.get('state_dict', ckpt)
        sd = {(k[len('generator.'):] if k.startswith('generator.') else k): v
              for k, v in sd.items()}
        missing, unexpected = model.load_state_dict(sd, strict=False)
        print('checkpoint:', len(missing), 'missing (0이어야 정상)')
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = model.to(device).eval()
        rnd = (np.random.rand(4, 64, 64, 3) * 255).astype(np.float32)
        t = torch.from_numpy(rnd).div_(255.0).permute(0, 3, 1, 2).unsqueeze(0).to(device)
        with torch.no_grad():
            out = model(t)
        print('test inference:', tuple(out.shape), '(1, 4, 3, 256, 256)이어야 정상')
        if not torch.cuda.is_available():
            print('WARNING: GPU를 인식하지 못해 CPU로 동작 중입니다. 이 상태면 매우 느립니다. 이 화면을 캡처해서 보내 주세요.')
        print('SELFTEST ALL OK')
        return

    model = RealBasicVSRNet(
        mid_channels=64, num_propagation_blocks=20, num_cleaning_blocks=20,
        dynamic_refine_thres=255, spynet_pretrained=SPYNET_URL)

    ckpt = torch.load(args.checkpoint, map_location='cpu', weights_only=False)
    sd = ckpt.get('state_dict', ckpt)
    sd = {(k[len('generator.'):] if k.startswith('generator.') else k): v
          for k, v in sd.items()}
    missing, unexpected = model.load_state_dict(sd, strict=False)
    print(f'checkpoint loaded: {len(missing)} missing (0이어야 정상)')

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print('device:', device)
    model = model.to(device).eval()

    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        raise SystemExit(f'cannot open {args.input}')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    while True:
        ok, f = cap.read()
        if not ok: break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()
    n = len(frames)
    print(f'{n} frames read, fps={fps:.3f}')
    if n == 0: raise SystemExit('no frames')

    writer = None
    if args.video is None and args.output:
        os.makedirs(args.output, exist_ok=True)
    t0 = time.time()
    with torch.no_grad():
        for s in range(0, n, args.max_seq_len):
            chunk = frames[s:s + args.max_seq_len]
            t = torch.from_numpy(np.stack(chunk)).float().div_(255.0)
            t = t.permute(0, 3, 1, 2).unsqueeze(0).to(device)  # (1,T,C,H,W)
            out = model(t)  # (1,T,C,4H,4W)
            out = (out.squeeze(0).permute(0, 2, 3, 1)
                   .clamp(0, 1).mul(255).round().byte().cpu().numpy())
            for i, img in enumerate(out):
                bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                if args.video:
                    if writer is None:
                        h, w = bgr.shape[:2]
                        writer = cv2.VideoWriter(
                            args.video, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                        print('output size:', w, 'x', h)
                    writer.write(bgr)
                else:
                    cv2.imwrite(os.path.join(args.output, f'{s + i:06d}.png'), bgr)
            print(f'chunk {s}-{s + len(chunk) - 1} done ({time.time() - t0:.0f}s)')
    if writer is not None:
        writer.release()
    print('DONE', f'{time.time() - t0:.0f}s total')
    if args.video:
        print('saved:', args.video, '(무음 - BGM은 나중에)')

if __name__ == '__main__':
    main()
