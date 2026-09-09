import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import validator from 'gltf-validator';
import {saveScreenshot} from './save_screenshot.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/t88510/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const styles=['bohemian','industrial','eclectic','wabisabi'];
const report={date:'2026-09-10 UTC+8',models:{},views:[],errors:[],physicalAndroidTested:false};
for(const file of ['house.glb','surroundings.glb',...styles.map(s=>`styles/${s}.glb`)]){
 const b=fs.readFileSync('output/'+file);const r=await validator.validateBytes(new Uint8Array(b),{maxIssues:10000});
 report.models[file]={bytes:b.length,errors:r.issues.numErrors,warnings:r.issues.numWarnings,messages:r.issues.messages};
 if(file==='house.glb')fs.writeFileSync('output/glb-validation.json',JSON.stringify(r,null,2));
 console.log(file,r.issues.numErrors,r.issues.numWarnings);
}
fs.writeFileSync('output/realism/glb-validation.json',JSON.stringify(report.models,null,2));
const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 page.on('pageerror',e=>report.errors.push(e.message));
 const network=[];page.on('requestfailed',r=>report.errors.push('Request failed: '+r.url()));
 page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
 const url=process.env.VIEWER_URL||'http://localhost:8876/index.html';
 await page.goto(url,{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.houseViewer?.gltf&&window.houseViewer?.realism.ready,{timeout:120000});
 await page.waitForTimeout(1200);await saveScreenshot(page,'output/realism/exterior.png');
 await page.getByRole('button',{name:'看街道與周邊',exact:true}).click();await page.waitForTimeout(750);
 await saveScreenshot(page,'output/realism/site-context.png');
 await page.locator('#hv-context').uncheck();
 report.contextHide=await page.evaluate(()=>!window.houseViewer.realism.surroundings.visible);
 await page.locator('#hv-context').check();
 for(const style of styles){
  await page.locator('#hv-style').selectOption(style);await page.waitForFunction(s=>window.houseViewer?.style===s,style,{timeout:90000});
  await page.getByRole('button',{name:'二樓室內視角',exact:true}).click();await page.waitForTimeout(900);
  if(!await page.evaluate(()=>!!window.houseViewer.scene.getObjectByName('INTERIOR_CEILING_PREVIEW')))report.errors.push('Missing interior ceiling preview');
  await saveScreenshot(page,`output/realism/${style}-interior.png`);
  const state=await page.evaluate(()=>{let maps=0,normals=0,shadowed=0;window.houseViewer.gltf.scene.traverse(o=>{if(o.isMesh){if(o.material.map)maps++;if(o.material.normalMap)normals++;if(o.receiveShadow)shadowed++;}});return {style:window.houseViewer.style,maps,normals,shadowed,...window.houseViewer.realism.stats()};});report.views.push(state);
 }
 for(const [i,word] of ['一','二','三','四'].entries()){
  await page.getByRole('button',{name:`只看${word}樓`,exact:true}).click();
  const visible=await page.evaluate(()=>['FLOOR_1','FLOOR_2','FLOOR_3','FLOOR_4','ROOF'].filter(n=>window.houseViewer.gltf.scene.getObjectByName(n).visible));
  if(visible.join()!==`FLOOR_${i+1}`)report.errors.push('Floor isolation failed '+word);
  if(await page.evaluate(()=>!!window.houseViewer.scene.getObjectByName('INTERIOR_CEILING_PREVIEW')))report.errors.push('Interior ceiling did not clear');
 }
 await page.getByRole('button',{name:'顯示全部',exact:true}).click();await page.locator('#hv-grp-ROOF').uncheck();
 report.roofHidden=await page.evaluate(()=>!window.houseViewer.gltf.scene.getObjectByName('ROOF').visible);
 const before=await page.evaluate(()=>window.houseViewer.camera.position.toArray());
 await page.mouse.move(400,350);await page.mouse.wheel(0,-240);await page.mouse.down();await page.mouse.move(500,380,{steps:6});await page.mouse.up();await page.waitForTimeout(300);
 const after=await page.evaluate(()=>window.houseViewer.camera.position.toArray());report.orbitAndZoom=JSON.stringify(before)!==JSON.stringify(after);
 await page.setViewportSize({width:412,height:915});await page.locator('#hv-quality').selectOption('balanced');
 await page.getByRole('button',{name:'二樓室內視角',exact:true}).click();await page.waitForTimeout(400);await saveScreenshot(page,'output/realism/mobile.png');
 report.mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,quality:window.houseViewer.realism.quality,selectorEnabled:!document.querySelector('#hv-style').disabled,assets:window.houseViewer.realism.assetStatus}));
 const cdp=await page.context().newCDPSession(page);await cdp.send('Emulation.setTouchEmulationEnabled',{enabled:true});
 const touchBefore=await page.evaluate(()=>window.houseViewer.camera.position.toArray());
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:150,y:230}]});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:220,y:260}]});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await page.waitForTimeout(200);
 const touchAfter=await page.evaluate(()=>window.houseViewer.camera.position.toArray());report.touchRotation=JSON.stringify(touchBefore)!==JSON.stringify(touchAfter);
 await page.close();
 // Offline single-file deliverable must not depend on external assets.
 const offline=await browser.newPage({viewport:{width:412,height:915}});const external=[];
 offline.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url())});offline.on('pageerror',e=>report.errors.push('offline: '+e.message));
 await offline.goto(pathToFileURL(path.resolve('output/住宅3D檢視器.html')).href,{waitUntil:'domcontentloaded'});
 await offline.waitForFunction(()=>window.houseViewer?.gltf&&window.houseViewer.realism.ready,{timeout:120000});
 await offline.locator('#hv-style').selectOption('wabisabi');await offline.waitForFunction(()=>window.houseViewer?.style==='wabisabi',{timeout:90000});
 report.offline={externalRequests:external,loaded:true};
}finally{await browser.close();}
report.passed=!report.errors.length&&Object.values(report.models).every(x=>x.errors===0)&&report.views.every(x=>x.maps>45&&x.normals>45)&&report.contextHide&&report.roofHidden&&report.orbitAndZoom&&report.touchRotation&&report.mobile.scrollWidth===report.mobile.width&&report.offline.externalRequests.length===0;
fs.writeFileSync('output/realism/viewer-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify({...report,models:Object.fromEntries(Object.entries(report.models).map(([k,v])=>[k,{errors:v.errors,warnings:v.warnings}]))}));
if(!report.passed)process.exitCode=1;
