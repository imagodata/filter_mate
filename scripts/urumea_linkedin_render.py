"""Edit the real 5.1.3 Urumea take with measured French narration. No generated map imagery."""
import argparse,bisect,hashlib,json,math,os,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

W,H,FPS=1920,1080,25
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
BG=(15,31,44);INK=(247,250,251);BLUE=(63,178,211)
TITLES={'hook':'Un filtre. Un résultat rejouable.','place':'San Sebastián / Donostia · Urumea',
 'relief':'1 · Ajouter le modèle de surface','altitude':'2 · Moyenne par emprise de bâtiment',
 'filtre':'3 · Filtrer plusieurs couches','favori':'4 · Conserver le filtre',
 'reset':'5 · Revenir à la carte complète','rejeu':'6 · Rejouer et vérifier','export':'7 · Exporter le résultat','fin':'FilterMate 5.1.3'}


def font(size,bold=False):return ImageFont.truetype(BOLD if bold else FONT,size)
def wrap(draw,text,face,width):
 lines=[];line=''
 for word in text.split():
  proposal=(line+' '+word).strip()
  if line and draw.textlength(proposal,font=face)>width:lines.append(line);line=word
  else:line=proposal
 return lines+[line] if line else lines

def pill(frame,text,xy,size=30,fill=(15,31,44,235),ink=INK):
 face=font(size,True);d=ImageDraw.Draw(frame);width=int(d.textlength(text,font=face))+40;x,y=xy
 overlay=Image.new('RGBA',frame.size,(0,0,0,0));draw=ImageDraw.Draw(overlay)
 draw.rounded_rectangle((x,y,x+width,y+size+30),radius=17,fill=fill)
 draw.text((x+20,y+8),text,font=face,fill=(*ink,255));frame.alpha_composite(overlay)

def subtitle(frame,text):
 d=ImageDraw.Draw(frame);face=font(32);lines=wrap(d,text,face,1580)
 height=42*len(lines)+24;y=H-110-height
 overlay=Image.new('RGBA',frame.size,(0,0,0,0));draw=ImageDraw.Draw(overlay)
 draw.rounded_rectangle((120,y,W-120,y+height),radius=17,fill=(12,25,36,235))
 for line in lines:
  width=draw.textlength(line,font=face);draw.text(((W-width)/2,y+10),line,font=face,fill=(*INK,255));y+=42
 frame.alpha_composite(overlay)

def credits(frame):
 d=ImageDraw.Draw(frame)
 text='© OpenStreetMap contributors (ODbL) · Copernicus DEM © DLR / Airbus · Union européenne / ESA'
 face=font(19);width=d.textlength(text,font=face)
 d.rounded_rectangle((72,H-63,90+width,H-22),radius=9,fill=(15,31,44,225))
 d.text((82,H-57),text,font=face,fill=(*INK,255))

def srt_time(seconds):
 ms=int(round(seconds*1000));return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--take',type=Path,required=True);parser.add_argument('--root',type=Path,default=Path('/w'))
 args=parser.parse_args();root=args.root;take=args.take;out=root/'final';out.mkdir(exist_ok=True)
 meta=json.loads((take/'meta.json').read_text());assert meta.get('status')=='complete',meta.get('error')
 times=meta['frames'];events=meta['events'];marks={e['name']:e['t'] for e in events if e['kind']=='mark'}
 observed={stage:json.loads((take/(stage+'-observed.json')).read_text()) for stage in ('relief','altitude','filtre','favori','reset','rejeu','export')}
 assert observed['reset']['filters']=={}
 verification=json.loads((take/'verified-observations.json').read_text());assert verification['verified']
 comparison={name:{'before':count,'after':verification['exported_counts'][name]} for name,count in verification['expected_counts_from_real_filter_tools'].items()}
 assert comparison and all(v['before']==v['after'] for v in comparison.values())
 specification=json.loads((root/'voice/narration.fr.json').read_text());durations=json.loads((root/'voice/durations.json').read_text())
 map_event=next(e for e in events if e['kind']=='camera' and e['t']>marks['done:relief'] and e['rect'][2]<meta['size'][0]*0.85)
 x,y,mw,mh=map_event['rect'];map_box=(max(0,x),max(0,y),min(meta['size'][0],x+mw),min(meta['size'][1],y+mh))
 cache={}
 def raw(timestamp):
  index=max(0,min(len(times)-1,bisect.bisect_right(times,timestamp)-1))
  if index not in cache:
   cache.clear();cache[index]=Image.open(take/'frames'/f'{index:06d}.jpg').convert('RGB')
  return cache[index]
 def map_image(timestamp):return raw(timestamp).crop(map_box)
 before=map_image(marks['still:result-reset']);after=map_image(marks['still:result-rejeu'])
 # A different pixel map and restored counters are both required for the before/after claim.
 from PIL import ImageChops,ImageStat
 assert sum(ImageStat.Stat(ImageChops.difference(before,after)).mean)>4,'No visible map change'
 segments=[];clock=0
 for line in specification['lines']:
  key=line['id'];duration=max(3.4,durations[key]['duration_s']+0.75)
  if key=='fin':duration+=0.7
  duration=math.ceil(duration*FPS)/FPS
  part={'id':key,'text':line.get('caption',line['text']),'start_s':round(clock,3),'duration_s':round(duration,3)}
  if key not in ('hook','place','fin'):
   clicks=[e['t'] for e in events if e['kind']=='click' and marks['ask:'+key]<e['t']<marks['done:'+key]]
   part['source_start_s']=max(marks['ask:'+key],(clicks[1]-0.5 if len(clicks)>1 else marks['done:'+key]-6))
   part['source_action_end_s']=marks['done:'+key]+0.35
   part['source_hold_s']=marks['still:result-'+key]
  segments.append(part);clock+=duration
 (out/'urumea-linkedin.fr.edl.json').write_text(json.dumps({'package':json.loads((root/'package.json').read_text()),'segments':segments,'duration_s':clock,'frame_source':'real QGIS capture; waits edited and results held; plugin unchanged','replay_comparison':comparison},ensure_ascii=False,indent=2)+'\n')
 subtitles=[];cues=[]
 for part in segments:
  words=part['text'].split();chunks=[];chunk=[]
  for word in words:
   if chunk and (len(' '.join(chunk+[word]))>105 or chunk[-1].endswith(('.',':','?'))):chunks.append(chunk);chunk=[]
   chunk.append(word)
  if chunk:chunks.append(chunk)
  cursor=part['start_s'];voice_duration=durations[part['id']]['duration_s']
  for words_ in chunks:
   end=cursor+voice_duration*len(words_)/len(words);text=' '.join(words_)
   subtitles.append(f'{len(subtitles)+1}\n{srt_time(cursor)} --> {srt_time(end)}\n{text}\n')
   cues.append((cursor,end,text));cursor=end
 (out/'urumea-linkedin.fr.srt').write_text('\n'.join(subtitles),encoding='utf-8')
 def compose(part,local):
  key=part['id'];duration=part['duration_s']
  if key=='hook':
   frame=Image.new('RGBA',(W,H),(*BG,255));d=ImageDraw.Draw(frame)
   d.text((78,58),'FilterMate 5.1.3',font=font(52,True),fill=(*INK,255))
   d.text((80,128),'Urumea · un filtre, plusieurs couches',font=font(32),fill=(*BLUE,255))
   for picture,left,label in [(before,72,'Carte complète'),(after,994,'Favori rejoué')]:
    image=picture.copy();image.thumbnail((850,720),Image.Resampling.LANCZOS)
    frame.alpha_composite(image.convert('RGBA'),(left+(850-image.width)//2,218+(720-image.height)//2))
    d.text((left+20,178),label,font=font(28,True),fill=(*INK,255))
   return frame
  if key=='fin':
   frame=Image.new('RGBA',(W,H),(*BG,255));d=ImageDraw.Draw(frame)
   d.text((140,220),'FilterMate 5.1.3',font=font(96,True),fill=(*INK,255))
   d.text((145,355),'Dans QGIS · gratuit et open source',font=font(44),fill=(*BLUE,255))
   for j,text in enumerate(['Un filtre géographique. Des résultats rejouables.','Modèle de surface 30 m · seuils illustratifs','Pas une évaluation du risque.']):
    d.text((145,478+j*74),text,font=font(38 if j==0 else 32,j==0),fill=(*INK,255))
   return frame
  if key=='place':timestamp=marks['still:baseline']
  else:
   action=min(4.0,duration*0.58)
   if local<action:
    timestamp=part['source_start_s']+(part['source_action_end_s']-part['source_start_s'])*local/action
   else:timestamp=part['source_hold_s']
  frame=raw(timestamp).resize((W,H),Image.Resampling.LANCZOS).convert('RGBA')
  pill(frame,TITLES[key],(65,34),size=29)
  if key in ('filtre','favori','reset','rejeu'):
   pill(frame,'Seuils illustratifs · 5 m / 200 m / 300 m',(65,100),size=22,fill=(23,67,86,230))
  if key in ('filtre','reset','rejeu') and local>=min(4.0,duration*0.58):
   data=observed['rejeu' if key=='rejeu' else ('filtre' if key=='filtre' else 'altitude')]
   candidates=[l for l in data['layers'] if 'altitude' in l['name'].lower()]
   if candidates:pill(frame,f"{candidates[0]['count']} bâtiments",(W-445,34),size=26,fill=(242,186,71,245),ink=(28,37,43))
  return frame
 silent=out/'urumea-linkedin.fr.silent.mp4'
 encode=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
                         '-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(silent)],stdin=subprocess.PIPE)
 thumbs=[];every=clock/16;index=0;sample_times=[]
 for part in segments:
  count=round(part['duration_s']*FPS)
  for n in range(count):
   local=n/FPS;to=part['start_s']+local;frame=compose(part,local)
   cue=next((text for start,end,text in cues if start<=to<end),None)
   if cue:subtitle(frame,cue)
   credits(frame)
   if part['id'] not in ('hook','fin'):
    d=ImageDraw.Draw(frame);d.text((W-410,H-54),'Séquences montées · attentes accélérées',font=font(15),fill=(20,40,54,255))
   rgb=frame.convert('RGB');encode.stdin.write(rgb.tobytes());index+=1
   if len(thumbs)<16 and to>=len(thumbs)*every:thumbs.append((to,rgb.resize((400,225),Image.Resampling.LANCZOS)))
  print('rendered',part['id'],flush=True)
 encode.stdin.close();assert encode.wait()==0
 inputs=[];filters=[];labels=[]
 for i,part in enumerate(segments):
  inputs+=['-i',str(root/'voice'/(part['id']+'.mp3'))]
  delay=round(part['start_s']*1000);filters.append(f'[{i+1}:a]adelay={delay}:all=1[a{i}]');labels.append(f'[a{i}]')
 filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[audio]')
 video=out/'urumea-linkedin-5.1.3-fr.mp4'
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),*inputs,'-filter_complex',';'.join(filters),'-map','0:v','-map','[audio]',
                 '-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-t',str(index/FPS),'-movflags','+faststart',str(video)],check=True)
 cover=compose(segments[0],0);credits(cover);cover.convert('RGB').save(out/'urumea-linkedin-cover.jpg',quality=93)
 sheet=Image.new('RGB',(1600,980),(23,31,38));d=ImageDraw.Draw(sheet)
 for i,(to,im) in enumerate(thumbs):
  x,y=(i%4)*400,(i//4)*245;sheet.paste(im,(x,y));d.text((x+8,y+226),f'{to:.1f} s',font=font(13),fill=(240,245,247))
 sheet.save(out/'urumea-linkedin-sheet.jpg',quality=90)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels','-of','json',str(video)],text=True))
 assert any(s['codec_type']=='audio' and s['codec_name']=='aac' for s in probe['streams'])
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(video),'-f','null','-'],check=True)
 receipt={'video':video.name,'bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'probe':probe,
          'full_decode_check':'passed','package':json.loads((root/'package.json').read_text()),'replay_comparison':comparison,
          'source_take':str(take),'raw_frames':len(times),'narration':specification,'publication':'not_uploaded','verification':verification}
 (out/'urumea-linkedin-validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'video':str(video),'duration_s':probe['format']['duration'],'bytes':video.stat().st_size,'audio':'AAC stereo48kHz','full_decode_check':'passed'}),flush=True)

if __name__=='__main__':main()
