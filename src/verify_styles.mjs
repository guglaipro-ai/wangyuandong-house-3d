import {saveScreenshot} from './save_screenshot.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import validator from 'gltf-validator';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/t88510/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const styles=['bohemian','industrial','eclectic','wabisabi'];
const report={models:{},views:[],errors:[],physicalAndroidTested:false};
for(const style of styles){
 const bytes=fs.readFileSync(`output/styles/${style}.glb`);
 const r=await validator.validateBytes(new Uint8Array(bytes),{maxIssues:30});
 report.models[style]={bytes:bytes.length,errors:r.issues.numErrors,warnings:r.issues.numWarnings,messages:r.issues.messages};
}
const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
try {
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto(process.env.VIEWER_URL||pathToFileURL(path.resolve('output/住宅3D檢視器.html')).href);
 await page.waitForFunction(()=>window.houseViewer?.gltf,{timeout:60000});
 for(const style of [...styles,'original']){
  await page.locator('#hv-style').selectOption(style);
  await page.waitForFunction(s=>window.houseViewer?.style===s,style,{timeout:60000});
  await page.waitForTimeout(400);
  const state=await page.evaluate(()=>{
   const meshes=[];window.houseViewer.gltf.scene.traverse(o=>{if(o.isMesh)meshes.push(o)});
   return {style:window.houseViewer.style,furnitureMeshes:meshes.filter(m=>m.userData.kind==='furniture').length,groups:['FLOOR_1','FLOOR_2','FLOOR_3','FLOOR_4','ROOF'].map(n=>({name:n,present:!!window.houseViewer.gltf.scene.getObjectByName(n)})),labels:document.querySelectorAll('.hv-room-label').length};
  });
  report.views.push(state);
  if(style==='original')continue;
  await saveScreenshot(page,`output/previews/${style}-floor2.png`);
  await page.getByRole('button',{name:'二樓室內視角',exact:true}).click();
  await page.waitForTimeout(350);
  await saveScreenshot(page,`output/previews/${style}-interior.png`);
 }
 await page.setViewportSize({width:412,height:915});
 await page.locator('#hv-style').selectOption('bohemian');
 await page.waitForFunction(()=>window.houseViewer?.style==='bohemian');
 await saveScreenshot(page,'output/previews/styles-mobile.png');
 report.mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,selectorEnabled:!document.querySelector('#hv-style').disabled}));
 await page.setViewportSize({width:1280,height:900});
 for(const [i,word] of ['一','二','三','四'].entries()){
  await page.getByRole('button',{name:`只看${word}樓`,exact:true}).click();
  await page.waitForTimeout(150);
  await saveScreenshot(page,`output/previews/furnished-floor-${i+1}.png`);
  const visible=await page.evaluate(()=>['FLOOR_1','FLOOR_2','FLOOR_3','FLOOR_4','ROOF'].filter(n=>window.houseViewer.gltf.scene.getObjectByName(n).visible));
  if(visible.join()!==`FLOOR_${i+1}`)report.errors.push('Floor isolation failed');
 }
} finally {await browser.close();}
fs.writeFileSync('output/styles/validation.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
if(report.errors.length||Object.values(report.models).some(m=>m.errors)||report.views.some(v=>v.groups.some(g=>!g.present)||(v.style!=='original'&&!v.furnitureMeshes))||report.mobile.scrollWidth>report.mobile.width)process.exitCode=1;
