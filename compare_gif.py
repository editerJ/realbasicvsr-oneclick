# 비교 GIF 만들기 - 원본과 보정본을 나란히 붙인 GIF 생성
# 사용: python compare_gif.py 원본.avi [보정본.mp4]
#   - 파일 1개만 주면 같은 폴더에서 짝(이름_영상보정.mp4)을 자동으로 찾음
#   - 파일 2개 주면 이름에 _영상보정 이 들어간 쪽이 보정본
# v2: 회전 메타데이터 수동 적용(자동회전 비활성화 후 명시 회전, 보정본에도 같은 회전 적용)
#     좌우 시간 정렬은 프레임 번호 기준 (보정본은 원본과 프레임 수가 같으므로 프레임이 곧 시간축)
import os, re, sys, shutil, subprocess

SUFFIX = '_영상보정'
EXTS = ['.mp4', '.avi', '.mov', '.mkv', '.mpg', '.mpeg', '.mts', '.wmv']
FONT = os.environ.get('COMPARE_GIF_FONT', 'C\\:/Windows/Fonts/malgun.ttf')
MAXFRAMES = 240   # 각 쪽 앞 240프레임까지 (30fps 기준 앞 8초 분량)
STEP = 3          # 3프레임마다 1장 추림
GIF_FPS = 10

def find_pair(path):
    d = os.path.dirname(os.path.abspath(path))
    stem, ext = os.path.splitext(os.path.basename(path))
    if SUFFIX in stem:
        base = stem.replace(SUFFIX, '')
        for e in EXTS:
            cand = os.path.join(d, base + e)
            if os.path.exists(cand):
                return cand, path
        return None, path
    cand = os.path.join(d, stem + SUFFIX + '.mp4')
    if os.path.exists(cand):
        return path, cand
    return path, None

def find_ffmpeg():
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    print('ffmpeg 준비 중... (최초 한 번, 약 25MB 다운로드)')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'imageio-ffmpeg'])
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def probe_rotation(ff, path):
    try:
        r = subprocess.run([ff, '-hide_banner', '-i', path],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        txt = r.stderr or ''
        m = re.search(r'rotate\s*:\s*(-?\d+)', txt)
        if not m:
            m = re.search(r'displaymatrix: rotation of (-?[\d.]+) degrees', txt)
        if m:
            return int(float(m.group(1))) % 360
    except Exception:
        pass
    return 0

def rotation_filter(deg):
    return {90: 'transpose=1', 270: 'transpose=2', 180: 'hflip,vflip'}.get(deg, '')

def build_filter(w, h, rot, with_labels):
    rf = (rotation_filter(rot) + ',') if rot else ''
    pick = f"select='lt(n,{MAXFRAMES})*not(mod(n,{STEP}))',setpts=N/({GIF_FPS}*TB)"
    cell = f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black'
    g = f'[0:v]{rf}{pick},{cell}[l];[1:v]{rf}{pick},{cell}[r];[l][r]hstack=2[hs];'
    bar = 'pad=iw:ih+38:0:38:color=0x141414'
    if with_labels:
        bar += (f",drawtext=fontfile='{FONT}':text='원본':fontcolor=white:fontsize=26:x=14:y=7"
                f",drawtext=fontfile='{FONT}':text='보정본':fontcolor=white:fontsize=26:x={w+14}:y=7")
    g += f'[hs]{bar}[vid];[vid]split[m][n];'
    g += '[m]palettegen=max_colors=160:stats_mode=diff[pal];'
    g += '[n][pal]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle[out]'
    return g

def make_gif(ff, orig, enh, out, w, h, rot, with_labels):
    cmd = [ff, '-y', '-loglevel', 'error',
           '-noautorotate', '-i', orig, '-noautorotate', '-i', enh,
           '-filter_complex', build_filter(w, h, rot, with_labels),
           '-map', '[out]', out]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode == 0 and os.path.exists(out), r.stderr.strip()

def main():
    args = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if len(args) == 1:
        orig, enh = find_pair(args[0])
    elif len(args) >= 2:
        a, b = args[0], args[1]
        if SUFFIX in os.path.basename(b):
            orig, enh = a, b
        elif SUFFIX in os.path.basename(a):
            orig, enh = b, a
        else:
            orig, enh = a, b
    else:
        print('영상 파일을 찾을 수 없습니다.')
        return 1
    if not orig or not enh:
        print('[오류] 짝이 맞는 영상을 찾지 못했습니다.')
        print('원본과 보정본(이름_영상보정.mp4)을 같은 폴더에 두거나, 두 파일을 같이 끌어다 놓으세요.')
        return 1
    out = os.path.join(os.path.dirname(os.path.abspath(orig)),
                       os.path.splitext(os.path.basename(orig))[0] + '_비교.gif')
    print('원본  :', orig)
    print('보정본:', enh)
    print('출력  :', out)
    ff = find_ffmpeg()
    rot = probe_rotation(ff, orig) or probe_rotation(ff, enh)
    if rot:
        print(f'회전 메타데이터 감지: {rot}도 - 바로 세워서 합칩니다')
    for labels in (True, False):
        ok, err = make_gif(ff, orig, enh, out, 480, 360, rot, labels)
        if ok:
            break
        if labels:
            print('라벨 없이 다시 시도합니다...')
        else:
            print('[오류] GIF 생성 실패:', err[:400])
            return 1
    size = os.path.getsize(out)
    if size > 20 * 1024 * 1024:
        print('GIF가 20MB를 넘어서 더 작게 다시 만듭니다...')
        ok, err = make_gif(ff, orig, enh, out, 400, 300, rot, labels)
        if ok:
            size = os.path.getsize(out)
    print(f'[완료] {out} ({size/1024/1024:.1f}MB)')
    return 0

if __name__ == '__main__':
    sys.exit(main())
