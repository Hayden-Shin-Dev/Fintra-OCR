/* 제작자: 신민철 | 이메일: min.developer.acc@gmail.com */
const endpointApi='https://api.github.com/repos/Hayden-Shin-Dev/Fintra-OCR/contents/endpoint.json?ref=fintra-live';
function validEndpoint(record){return record?.online===true&&/^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/.test(record.origin);}
async function fetchTimed(url){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);try{const response=await fetch(url,{signal:controller.signal,cache:'no-store',credentials:'omit'});if(!response.ok)throw Error('unavailable');return await response.json();}finally{clearTimeout(timer);}}
async function connect(){
 const heading=document.getElementById('heading'),status=document.getElementById('status'),retry=document.getElementById('retry'),spinner=document.getElementById('spinner');
 retry.hidden=true;spinner.hidden=false;heading.textContent='Fintra에 연결하고 있어요';status.textContent='현재 서버 주소를 확인하고 있습니다.';
 try{
  const file=await fetchTimed(endpointApi+'&t='+Date.now());
  const record=JSON.parse(atob(file.content.replace(/\s/g,'')));
  if(!validEndpoint(record))throw Error('offline');
  status.textContent='서버가 준비됐는지 확인하고 있습니다.';
  const health=await fetchTimed(record.origin+'/api/public-health?t='+Date.now());
  if(health.service!=='fintra'||health.online!==true)throw Error('offline');
  status.textContent='로그인 화면으로 이동합니다.';location.replace(record.origin+'/');
 }catch(error){heading.textContent='지금은 연결할 수 없습니다';status.textContent='서버가 꺼져 있거나 연결을 준비 중일 수 있습니다. 잠시 후 다시 연결해 주세요.';retry.hidden=false;spinner.hidden=true;}
}
if(typeof document!=='undefined'){document.getElementById('retry').onclick=connect;connect();}
if(typeof module!=='undefined')module.exports={validEndpoint};
