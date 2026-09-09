import fs from 'node:fs';
export async function saveScreenshot(page,target){
 const bytes=await page.screenshot();
 fs.writeFileSync(target+'.tmp',bytes);
 fs.renameSync(target+'.tmp',target);
}
