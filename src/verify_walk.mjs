// 170 cm first-person walk: entry steps, wall collision, stair climb, touch joystick,
// style switching while walking, and per-style eye-level screenshots.
import fs from 'node:fs';
import {createRequire} from 'node:module';
import {saveScreenshot} from './save_screenshot.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/t88510/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
fs.mkdirSync('output/walk',{recursive:true});
const report={date:'2026-09-28 UTC+8',stature_m:1.70,eye_m:1.58,tests:{},errors:[],physicalAndroidTested:false};
const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
try{
 const context=await browser.newContext({viewport:{width:1280,height:860}});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto(process.env.VIEWER_URL||'http://localhost:8876/index.html');
 await page.waitForFunction(()=>window.houseViewer?.gltf&&window.houseViewer.realism.ready,{timeout:240000});
 const st=()=>page.evaluate(()=>window.houseViewer.walk.state());
 const hold=async(k,ms)=>{await page.evaluate(k=>window.houseViewer.walk.press(k,true),k);await page.waitForTimeout(ms);await page.evaluate(k=>window.houseViewer.walk.press(k,false),k);await page.waitForTimeout(250);return st();};
 const place=(x,y,f,yaw)=>page.evaluate(a=>window.houseViewer.walk.place(...a,-.08),[x,y,f,yaw]);
 await page.locator('#hv-walk-start').selectOption('gate');await page.locator('#hv-walk').click();
 let s=await st();report.tests.enter={active:s.active,eye:s.eye,room:s.room};
 await saveScreenshot(page,'output/walk/gate.png');
 s=await hold('w',5000);report.tests.entrySteps={feet:s.feet,plan:s.plan,room:s.room,pass:s.feet>.5&&s.plan[1]>12.2};
 await place(10.6,8.0,4.812,0);s=await hold('w',3500);
 report.tests.wallCollision={plan:s.plan,pass:s.plan[1]>=6.0+.2-.01&&s.feet>4.7};
 await place(10.93,4.8,.612,0);await hold('w',6000);
 await place(...(await st()).plan,(await st()).feet,Math.PI/2);await hold('w',4500);
 await place(...(await st()).plan,(await st()).feet,Math.PI);s=await hold('w',6000);
 report.tests.stairClimb1to2={feet:s.feet,room:s.room,pass:Math.abs(s.feet-4.811)<.05};
 const ceilings=await page.evaluate(()=>{let c=0;window.houseViewer.gltf.scene.traverse(o=>{if(o.isMesh&&o.userData.kind==='ceiling'&&o.visible)c++});return c;});
 report.tests.ceilingsVisible={count:ceilings,pass:ceilings>0};
 const views={living2:[10.6,11.0,4.812,.3],kitchen:[12.9,4.9,4.812,-.35],gallery1:[5.3,14.3,.612,.25],terrace:[5.6,11.4,11.712,.8]};
 report.tests.styles={};
 for(const style of ['bohemian','industrial','eclectic','wabisabi']){
  await page.locator('#hv-style').selectOption(style);await page.waitForFunction(s=>window.houseViewer?.style===s,style,{timeout:240000});
  s=await st();report.tests.styles[style]={walkStillActive:s.active,collisionTriangles:s.triangles};
  for(const [name,v] of Object.entries(views)){await place(...v);await page.waitForTimeout(1300);await saveScreenshot(page,`output/walk/${style}-${name}.png`);}
  await place(9.3,9.8,4.812,0);s=await hold('w',2500);report.tests.styles[style].sofaBlocksWalk={plan:s.plan,pass:s.plan[1]>6.9};
 }
 await page.keyboard.press('Escape');report.tests.escapeExits={pass:!(await st()).active};
 await page.close();
 // Mobile portrait + touch joystick
 const mctx=await browser.newContext({viewport:{width:412,height:915},hasTouch:true,isMobile:true});
 const m=await mctx.newPage();m.on('pageerror',e=>report.errors.push('mobile: '+e.message));
 await m.goto(process.env.VIEWER_URL||'http://localhost:8876/index.html');
 await m.waitForFunction(()=>window.houseViewer?.gltf&&window.houseViewer.realism.ready,{timeout:240000});
 await m.locator('#hv-walk-start').selectOption('f2');await m.locator('#hv-walk').click();await m.waitForTimeout(600);
 const before=await m.evaluate(()=>window.houseViewer.walk.state());
 const joy=await m.locator('.walk-joy').boundingBox();const cdp=await mctx.newCDPSession(m);
 const cx=joy.x+joy.width/2,cy=joy.y+joy.height/2;
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:cx,y:cy,id:1}]});
 for(let i=1;i<=6;i++){await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:cx,y:cy-i*7,id:1}]});await m.waitForTimeout(80);}
 await m.waitForTimeout(1200);
 await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await m.waitForTimeout(300);
 const after=await m.evaluate(()=>window.houseViewer.walk.state());
 const lookBefore=after.yaw;
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:300,y:250,id:2}]});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:240,y:255,id:2}]});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await m.waitForTimeout(300);
 const looked=await m.evaluate(()=>window.houseViewer.walk.state());
 await saveScreenshot(m,'output/walk/mobile.png');
 report.tests.mobileJoystick={moved:Math.hypot(after.plan[0]-before.plan[0],after.plan[1]-before.plan[1]),turned:Math.abs(looked.yaw-lookBefore),scrollWidth:await m.evaluate(()=>document.documentElement.scrollWidth),pass:Math.hypot(after.plan[0]-before.plan[0],after.plan[1]-before.plan[1])>.3&&Math.abs(looked.yaw-lookBefore)>.05};
}finally{await browser.close();}
const flat=[...Object.values(report.tests).filter(t=>'pass' in t),...Object.values(report.tests.styles||{}).map(s=>s.sofaBlocksWalk)];
report.passed=!report.errors.length&&flat.every(t=>t.pass)&&Object.values(report.tests.styles).every(s=>s.walkStillActive);
fs.writeFileSync('output/walk/walk-validation.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
if(!report.passed)process.exitCode=1;
