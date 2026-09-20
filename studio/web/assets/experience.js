/* 제작자: 신민철 | 이메일: min.developer.acc@gmail.com */
import * as T from './three.module.js';

// One offscreen WebGL renderer; DOM-owned presentation canvases scroll with their hosts.
// Animation frequency must never control page positioning.
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const pointer={x:innerWidth/2,y:innerHeight/2,active:false};
const cursor=document.createElement('div');cursor.id='fintra-cursor';cursor.setAttribute('aria-hidden','true');document.body.append(cursor);
document.addEventListener('pointermove',e=>{pointer.x=e.clientX;pointer.y=e.clientY;pointer.active=e.pointerType!=='touch';cursor.style.transform=`translate3d(${e.clientX}px,${e.clientY}px,0)`;cursor.classList.toggle('interactive',!!e.target.closest('button,a,summary,[role=button]'));cursor.classList.toggle('text',!!e.target.closest('input,textarea'));cursor.classList.toggle('visible',pointer.active&&!e.target.closest('dialog'));const card=e.target.closest('.upload-card,.login-art');if(card&&!reduced.matches){const r=card.getBoundingClientRect();card.style.setProperty('--mx',`${e.clientX-r.x}px`);card.style.setProperty('--my',`${e.clientY-r.y}px`);card.style.setProperty('--tilt-x',`${-(e.clientY-r.y-r.height/2)/r.height*4}deg`);card.style.setProperty('--tilt-y',`${(e.clientX-r.x-r.width/2)/r.width*4}deg`)}});
document.addEventListener('pointerdown',()=>cursor.classList.add('pressed'));
document.addEventListener('pointerup',()=>cursor.classList.remove('pressed'));
document.documentElement.addEventListener('pointerleave',()=>{pointer.active=false;cursor.classList.remove('visible')});
document.addEventListener('keydown',e=>{if(e.key==='Tab')cursor.classList.remove('visible')});

const mat=(color,extra={})=>new T.MeshStandardMaterial({color,roughness:.43,metalness:.02,...extra});
const cream=mat('#fff2cb'),sage=mat('#273a57'),dark=mat('#302a29'),pink=mat('#efb4a3'),gold=mat('#c9ad69'),leafmat=mat('#81ae50'),white=mat('#ffffff');
function roundBox(w,h,d,r){const s=new T.Shape(),x=-w/2,y=-h/2;s.moveTo(x+r,y);s.lineTo(x+w-r,y);s.quadraticCurveTo(x+w,y,x+w,y+r);s.lineTo(x+w,y+h-r);s.quadraticCurveTo(x+w,y+h,x+w-r,y+h);s.lineTo(x+r,y+h);s.quadraticCurveTo(x,y+h,x,y+h-r);s.lineTo(x,y+r);s.quadraticCurveTo(x,y,x+r,y);const g=new T.ExtrudeGeometry(s,{depth:d,bevelEnabled:true,bevelSegments:3,steps:1,bevelSize:.045,bevelThickness:.045,curveSegments:8});g.translate(0,0,-d/2);return g}
const sphere=new T.SphereGeometry(1,20,14);
function mesh(parent,g,m,x=0,y=0,z=0){const o=new T.Mesh(g,m);o.position.set(x,y,z);o.castShadow=true;parent.add(o);return o}
function ball(parent,m,x,y,z,sx,sy,sz){const o=mesh(parent,sphere,m,x,y,z);o.scale.set(sx,sy,sz);return o}
function character(){
 const root=new T.Group(),body=new T.Group(),head=new T.Group();root.add(body);body.add(head);head.position.y=1.2;
 mesh(body,roundBox(.76,.73,.48,.15),sage,0,.25,0);mesh(body,roundBox(.24,.58,.025,.035),white,0,.3,.28);
 mesh(body,new T.ConeGeometry(.08,.22,4),gold,0,.38,.34).rotation.z=Math.PI;mesh(body,new T.SphereGeometry(.045,10,8),gold,0,.52,.35);for(let i=0;i<2;i++)ball(body,gold,.22,.28-i*.16,.28,.025,.025,.02);
 mesh(body,roundBox(.17,.1,.015,.015),white,-.21,.47,.29);
 mesh(head,roundBox(1.25,1.03,.68,.29),cream);mesh(head,roundBox(1.08,.82,.08,.2),cream,0,-.04,.39);ball(head,cream,-.62,.35,0,.19,.21,.17);ball(head,cream,.62,.35,0,.19,.21,.17);ball(head,pink,-.64,.35,.12,.09,.11,.025);ball(head,pink,.64,.35,.12,.09,.11,.025);
 const eyes=[ball(head,dark,-.27,.01,.51,.055,.075,.03),ball(head,dark,.27,.01,.51,.055,.075,.03)];
 ball(head,white,-.285,.032,.54,.013,.018,.009);ball(head,white,.255,.032,.54,.013,.018,.009);
 ball(head,pink,-.39,-.15,.505,.09,.045,.018);ball(head,pink,.39,-.15,.505,.09,.045,.018);
 const smile=new T.CatmullRomCurve3([new T.Vector3(-.085,-.15,.51),new T.Vector3(0,-.195,.52),new T.Vector3(.085,-.15,.51)]);mesh(head,new T.TubeGeometry(smile,12,.016,8,false),dark);
 // Horn-rimmed glasses: open geometry lenses preserve the animated eyes.
 for(const side of [-1,1]){const pts=[],cx=side*.275;for(let i=0;i<=48;i++){const a=i/48*Math.PI*2;pts.push(new T.Vector3(cx+Math.sign(Math.cos(a))*Math.pow(Math.abs(Math.cos(a)),.55)*.205,.015+Math.sign(Math.sin(a))*Math.pow(Math.abs(Math.sin(a)),.55)*.145,.565))}mesh(head,new T.TubeGeometry(new T.CatmullRomCurve3(pts),64,.031,8,false),dark);mesh(head,new T.BoxGeometry(.14,.038,.035),dark,side*.55,.045,.54)}
 mesh(head,new T.BoxGeometry(.14,.04,.04),dark,0,.045,.57);ball(head,gold,0,-.10,.51,.045,.032,.04);
 const arms=[];for(const side of [-1,1]){const arm=new T.Group();arm.position.set(side*.48,.48,0);body.add(arm);mesh(arm,new T.CapsuleGeometry(.1,.22,5,10),white,0,-.17,0);ball(arm,cream,0,-.36,.03,.13,.14,.13);arms.push(arm)}
 const legs=[];for(const side of [-1,1]){const leg=new T.Group();leg.position.set(side*.21,-.13,0);body.add(leg);mesh(leg,new T.CapsuleGeometry(.105,.18,5,10),sage,0,-.13,0);mesh(leg,roundBox(.29,.18,.4,.07),dark,0,-.3,.07);legs.push(leg)}
 const tablet=new T.Group();body.add(tablet);tablet.position.set(0,.18,.62);tablet.rotation.x=-.3;mesh(tablet,roundBox(.73,.43,.055,.04),dark);mesh(tablet,roundBox(.62,.31,.012,.02),white,0,0,.045);for(let i=0;i<3;i++)mesh(tablet,new T.BoxGeometry(.36-i*.07,.017,.01),sage,-.05,.08-i*.075,.115);
 const pen=mesh(arms[1],new T.CylinderGeometry(.024,.024,.4,8),gold,0,-.39,.13);pen.rotation.z=-.35;return {root,body,head,eyes,arms,legs,tablet,pen};
}
let renderer;
try{renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});}catch{document.documentElement.classList.add('no-webgl')}
if(renderer){
 document.documentElement.classList.add('has-3d');const canvas=renderer.domElement;canvas.setAttribute('aria-hidden','true');renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0,0);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35;renderer.autoClear=false;
 const scene=new T.Scene();scene.add(new T.HemisphereLight(0xffffff,0x718596,2.7));const key=new T.DirectionalLight(0xfff0d9,3.2);key.position.set(-3,5,5);scene.add(key);const rim=new T.DirectionalLight(0xb5d7ff,2.2);rim.position.set(3,2,-3);scene.add(rim);
 const model=character();scene.add(model.root);const camera=new T.PerspectiveCamera(30,1,.1,50);camera.position.set(0,1.05,6.5);camera.lookAt(0,.75,0);
 const surfaces=new WeakMap();
 let hosts=[],last=0,w=0,h=0;const refresh=()=>{last=0;hosts=[...document.querySelectorAll('[data-companion]')];hosts.forEach(el=>{if(!el.dataset.bound){el.dataset.bound='1';el.addEventListener('pointerenter',()=>el.dataset.greetUntil=String(performance.now()+2200));el.addEventListener('click',()=>el.dataset.greetUntil=String(performance.now()+1600))}})};
 new MutationObserver(refresh).observe(document.querySelector('#app'),{childList:true,subtree:true});new MutationObserver(refresh).observe(document.querySelector('#supporter'),{childList:true,subtree:true});new MutationObserver(refresh).observe(document.querySelector('#chat'),{childList:true,subtree:true});refresh();
 const clamp=(v,n)=>Math.max(-n,Math.min(n,v));
 function animate(now){requestAnimationFrame(animate);if(document.hidden||now-last<(reduced.matches?180:document.querySelector(".busy,.progress-view,.is-thinking")?83:33))return;last=now;
  const visible=hosts.filter(el=>el.isConnected&&el.checkVisibility()).map(el=>({el,r:el.getBoundingClientRect()})).filter(({r})=>r.width>0&&r.height>0&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth);
  if(!visible.length)return;
  const nextW=Math.ceil(Math.max(...visible.map(({r})=>r.width))),nextH=Math.ceil(Math.max(...visible.map(({r})=>r.height)));
  if(w!==nextW||h!==nextH){w=nextW;h=nextH;renderer.setSize(w,h,false)}

  const t=reduced.matches?0:now/1000;
  for(const {el,r} of visible){
   let surface=surfaces.get(el);
   if(!surface){const output=document.createElement('canvas');output.className='companion-surface';output.setAttribute('aria-hidden','true');el.append(output);surface={output,context:output.getContext('2d')};surfaces.set(el,surface)}
   if(!surface.context)continue;

   const hovered=pointer.active&&pointer.x>=r.left&&pointer.x<=r.right&&pointer.y>=r.top&&pointer.y<=r.bottom;
   const busy=!!el.closest('.busy,.progress-view,.boot,.is-thinking'),done=!!el.closest('.done');
   const wave=!reduced.matches&&(hovered||now<Number(el.dataset.greetUntil||0)||(!busy&&t%17>14));
   const targetX=pointer.active?clamp((pointer.x-r.left-r.width/2)/Math.max(r.width,150),.45):Math.sin(t*.34)*.13;
   const targetY=pointer.active?clamp((pointer.y-r.top-r.height/2)/Math.max(r.height,150),.18):0;
   model.head.rotation.set(busy?.18+Math.sin(t*2)*.025:targetY*.35,targetX*.5,Math.sin(t*.65)*.025);
   model.body.position.y=Math.sin(t*2)*.018;model.body.rotation.y=busy?-.12:targetX*.12;model.root.rotation.z=wave?Math.sin(t*3)*.018:0;
   const blink=!reduced.matches&&t%4.7<.14?.12:1;model.eyes.forEach(e=>e.scale.y=.075*blink);
   model.arms[0].rotation.z=busy?.55:-.12-Math.sin(t*1.7)*.06;
   model.arms[1].rotation.z=wave?1.95+Math.sin(t*13)*.3:busy?-.65:.12+Math.sin(t*1.7)*.06;
   model.arms.forEach((a,i)=>a.rotation.x=busy?-1.05+Math.sin(t*9+i)*.08:0);model.arms[1].position.y=busy?.48+Math.sin(t*8)*.035:.48;
   model.legs.forEach((l,i)=>l.rotation.x=!busy&&t%22>19?Math.sin(t*6+i*Math.PI)*.2:0);model.tablet.visible=busy;model.pen.visible=busy;
   model.root.position.y=done&&!reduced.matches?Math.max(0,Math.sin(t*3))*.045:0;
   camera.aspect=r.width/r.height;camera.updateProjectionMatrix();
   renderer.setScissorTest(false);renderer.clear();renderer.setViewport(0,h-r.height,r.width,r.height);renderer.render(scene,camera);
   const ratio=renderer.getPixelRatio(),pw=Math.max(1,Math.floor(r.width*ratio)),ph=Math.max(1,Math.floor(r.height*ratio));
   if(surface.output.width!==pw||surface.output.height!==ph){surface.output.width=pw;surface.output.height=ph}
   surface.context.clearRect(0,0,pw,ph);
   surface.context.drawImage(canvas,0,0,pw,ph,0,0,pw,ph);

   el.dataset.motion=reduced.matches?'reduced':busy?'working':wave?'waving':'idle';el.dataset.rendered='3d';
  }
 }
 requestAnimationFrame(animate);canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();document.documentElement.classList.add('no-webgl')});canvas.addEventListener('webglcontextrestored',()=>document.documentElement.classList.remove('no-webgl'));
}
