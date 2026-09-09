import {saveScreenshot} from './save_screenshot.mjs';
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);const {chromium}=require('C:/Users/t88510/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
const report={errors:[]};
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}});page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto(process.env.VIEWER_URL||pathToFileURL(path.resolve('output/住宅3D檢視器.html')).href);
 await page.waitForFunction(()=>window.houseViewer?.gltf,{timeout:60000});
 for(const [name,floor,eye,target] of [
  ['stair-detail','二',[10.4,10.8,6.4],[9.0,5.3,2.35]],
  ['bathroom-detail','三',[7.5,12.3,5.1],[5.7,8.7,2.9]],
  ['entry-detail','一',[15.5,3.2,7.0],[11.0,1.7,4.6]]
 ]){
  await page.getByRole('button',{name:`只看${floor}樓`,exact:true}).click();
  if(name==='entry-detail')await page.locator('#hv-cutaway').uncheck();
  await page.locator('#hv-labels').count().then(async count=>{if(count)await page.locator('#hv-labels').uncheck()});
  await page.evaluate(({eye,target})=>{const v=window.houseViewer;v.camera.position.set(eye[0]-7.18,eye[1],eye[2]-8.3);v.controls.target.set(target[0]-7.18,target[1],target[2]-8.3);v.controls.update();v.render()},{eye,target});
  await page.waitForTimeout(300);await saveScreenshot(page,`output/audit/${name}.png`);
 }
 const auditUrl=process.env.VIEWER_URL?new URL('audit/index.html',process.env.VIEWER_URL).href:pathToFileURL(path.resolve('output/audit/index.html')).href;
 await page.goto(auditUrl);report.rows=await page.locator('tbody tr').count();
 await page.locator('#q').fill('電梯');report.searchRows=await page.locator('tbody tr:visible').count();
 await page.setViewportSize({width:412,height:915});report.mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
 await saveScreenshot(page,'output/audit/checklist-mobile.png');
}finally{await browser.close()}
report.passed=report.rows>=100&&report.searchRows>0&&report.searchRows<report.rows&&!report.errors.length&&report.mobile.width===report.mobile.scrollWidth;
fs.writeFileSync('output/audit/viewer-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.passed)process.exitCode=1;
