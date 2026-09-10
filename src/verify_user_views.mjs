import fs from 'node:fs';
import {createRequire} from 'node:module';
import {saveScreenshot} from './save_screenshot.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/t88510/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const browser=await chromium.launch({headless:true,channel:'msedge',args:['--enable-unsafe-swiftshader']});
const results=[];
try{
 const page=await browser.newPage({viewport:{width:1400,height:1100}});
 await page.goto('http://localhost:8876/index.html');
 await page.waitForFunction(()=>window.houseViewer?.realism.ready,{timeout:120000});
 await page.locator('#hv-context').uncheck();
 await page.locator('#hv-style').selectOption('bohemian');
 await page.waitForFunction(()=>window.houseViewer?.style==='bohemian',{timeout:90000});
 for(const [i,word] of ['一','二','三','四'].entries()){
  await page.getByRole('button',{name:`只看${word}樓`,exact:true}).click();
  await page.evaluate(i=>{
   const v=window.houseViewer,b=[.6,4.8,8.4,11.7][i];
   v.camera.position.set(0,b+29,6);v.controls.target.set(0,b,0);v.controls.update();v.render();
  },i);
  await page.waitForTimeout(550);
  const file=`output/corrections/floor-${i+1}.png`;
  await saveScreenshot(page,file);
  results.push({floor:i+1,file,labels:await page.locator('.hv-room-label:visible').allTextContents()});
 }
}finally{await browser.close();}
fs.writeFileSync('output/corrections/view-validation.json',JSON.stringify(results,null,2));
console.log(JSON.stringify(results));
