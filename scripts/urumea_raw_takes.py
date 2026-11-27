"""Make reviewable silent MP4s of the complete real takes, preserving their clock."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    selected = [('acquisition','acquire04'),('analyse','analysis03'),('composition','composer02'),
                ('finition','finish01'),('relecture','review02')]

    def encode(entry):
        label,take = entry
        source = args.root / 'out' / take / 'urumea'
        meta = json.loads((source / 'meta.json').read_text())
        assert meta['status']=='complete'
        times = meta['frames']
        lines = ['ffconcat version 1.0']
        for i,stamp in enumerate(times):
            frame = source / 'frames' / f'{i:06d}.jpg'
            assert frame.is_file()
            dt = times[i+1]-stamp if i+1<len(times) else 1/15
            assert dt>0
            lines.extend([f"file '{frame}'",'option framerate 1000',f'duration {dt:.6f}'])
        lines.append(f"file '{frame}'")
        playlist = args.output / (label+'.ffconcat')
        playlist.write_text('\n'.join(lines)+'\n')
        target = args.output / (label+'.mp4')
        subprocess.run(['ffmpeg','-y','-v','error','-safe','0','-f','concat','-i',str(playlist),
                        '-vf','fps=15','-an','-c:v','libx264','-threads','2','-preset','veryfast',
                        '-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
        info = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size',
                                                   '-of','json',str(target)],text=True))['format']
        assert abs(float(info['duration'])-(times[-1]-times[0]))<.25
        return {'phase':label,'take':take,'file':target.name,'frames_captured':len(times),
                'duration_s':float(info['duration']),'bytes':int(info['size']),'audio':'silent raw footage',
                'timing':'Original capture timestamps; displayed at 15 fps without cuts or speed-up.'}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(encode,selected))
    (args.output/'takes-mp4.json').write_text(json.dumps({'takes':results,'publication':'not_published'},
                                                      ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(results,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
