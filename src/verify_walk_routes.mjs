// Drives the real 170 cm walk engine along the shortest walkable route to every room
// (routes from verify_circulation.py) and reports any room it cannot reach.
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/t88510/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const data=JSON.parse(fs.readFileSync('output/circulation/circulation.json','utf8')).results;
// Outdoor approach routes (plan metres, start at the gate on grade) through every exterior door.
const OUTDOOR={'正門 D2a':[[8.35,17.6],[8.35,15.6],[7.6,14.0],[5.6,14.0]],
 '東側大廳門 D2b':[[8.35,17.6],[14.9,16.0],[14.9,10.8],[13.2,10.8],[11.6,10.8]],
 '樓梯間門 D1':[[8.35,17.6],[14.9,16.0],[14.9,4.7],[12.6,4.7],[11.0,4.9]],
 '後門 D5a':[[8.35,17.6],[-.9,17.0],[-.9,-.5],[3.0,-.5],[4.7,-.45],[4.7,.9]]};
const BASE={1:.6,2:4.8,3:8.4,4:11.7};
const only=process.argv.slice(2);
const report={date:new Date().toISOString(),method:'Steer toward each waypoint at walking speed (W key); a leg fails if no 5 cm progress in 4 s (12 s on the first leg, which may wait for software-GL shader compilation).',styles:{},errors:[]};
const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
try{
 const page=await (await browser.newContext({viewport:{width:960,height:640}})).newPage();
 page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto(process.env.VIEWER_URL||'http://localhost:8876/index.html');
 await page.waitForFunction(()=>window.houseViewer?.gltf&&window.houseViewer.realism.ready,{timeout:240000});
 await page.locator('#hv-walk').click();
 for(const style of Object.keys(data)){
  if(only.length&&!only.includes(style))continue;
  const key=style==='empty'?'original':style;
  if(await page.evaluate(()=>window.houseViewer.style)!==key){
   await page.locator('#hv-style').selectOption(key);
   await page.waitForFunction(k=>window.houseViewer?.style===k,key,{timeout:240000});
   await page.waitForTimeout(800);
  }
  // wait until the collision grid has been rebuilt for this variant (triangle count stable)
  let prev=-1,same=0;
  for(let i=0;i<60&&same<3;i++){const n=await page.evaluate(()=>window.houseViewer.walk.state().triangles);same=n===prev&&n>0?same+1:0;prev=n;await page.waitForTimeout(500);}
  const rows=[];
  const outdoor=Object.fromEntries(Object.entries(OUTDOOR).map(([k,v])=>[k,{room:k,route:v}]));
  for(const [f,rooms] of [['0',Object.values(outdoor)],...Object.entries(data[style])]){
   for(const r of rooms){
    if(!r.route||r.route.length<2){rows.push({floor:+f,room:r.room,skipped:'no route'});continue;}
    const res=await page.evaluate(async({route,feet})=>{
     const w=window.houseViewer.walk;w.place(route[0][0],route[0][1],feet,0,-.05);
     const st=()=>w.state();let legs=0,t0=performance.now(),stuck=null;
     w.press('w',true);
     try{
      for(let i=1;i<route.length;i++){
       const [tx,ty]=route[i];let best=1e9,last=performance.now();
       while(true){
        const s=st();const dx=tx-s.plan[0],dy=ty-s.plan[1],d=Math.hypot(dx,dy);
        if(d<(i===route.length-1?.25:.32))break;
        // plan (dx,dy) -> world (dx,dz); forward = (-sin yaw, -cos yaw)
        w.look(Math.atan2(-dx,-dy),-.05);
        if(d<best-.05){best=d;last=performance.now();}
        if(performance.now()-last>(i===1?12000:4000)){stuck={leg:i,at:s.plan,feet:s.feet,target:[tx,ty],dist:d};break;}
        await new Promise(r=>setTimeout(r,40));
       }
       if(stuck)break;legs++;
      }
     }finally{w.press('w',false);}
     const s=st();return {legs,stuck,seconds:(performance.now()-t0)/1000,endRoom:s.room,feet:s.feet};
    },{route:r.route,feet:f==='0'?.02:BASE[f]+.012});
    rows.push({floor:+f,room:r.room,...res,pass:!res.stuck});
    console.log(style,f,r.room,res.stuck?'STUCK '+JSON.stringify(res.stuck):'ok '+res.seconds.toFixed(1)+'s');
   }
  }
  report.styles[style]=rows;
 }
}finally{await browser.close();}
report.passed=!report.errors.length&&Object.values(report.styles).every(rs=>rs.every(r=>r.pass!==false));
fs.writeFileSync('output/circulation/walk-routes.json',JSON.stringify(report,null,1));
console.log('passed',report.passed,report.errors);
if(!report.passed)process.exitCode=1;
