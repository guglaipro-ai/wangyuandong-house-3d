import * as THREE from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export function installRealism(renderer,scene,camera,requestRender,revision) {
 renderer.info.autoReset=false;
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
 renderer.toneMapping=THREE.AgXToneMapping;renderer.toneMappingExposure=1.05;
 scene.background=new THREE.Color('#d7e2e7');scene.fog=new THREE.FogExp2('#d7e2e7',.0018);
 const sun=new THREE.DirectionalLight(0xfff0db,4.2);sun.position.set(-30,48,24);sun.target.position.set(0,5,0);
 sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);
 Object.assign(sun.shadow.camera,{left:-29,right:29,top:29,bottom:-29,near:1,far:140});
 sun.shadow.bias=-.00015;sun.shadow.normalBias=.025;sun.shadow.radius=3;
 scene.add(sun,sun.target,new THREE.HemisphereLight(0xe5f1ff,0x8a816b,.12));
 const pmrem=new THREE.PMREMGenerator(renderer);
 const room=new RoomEnvironment();const fallback=pmrem.fromScene(room,.06);room.dispose();
 scene.environment=fallback.texture;scene.environmentIntensity=.45;
 let sky=null,environmentRT=fallback,surroundings=null;
 let quality=window.innerWidth>700?'high':'balanced';
 if(quality==='balanced')sun.shadow.mapSize.set(1024,1024);
 const composer=new EffectComposer(renderer);composer.renderTarget1.samples=4;composer.renderTarget2.samples=4;composer.addPass(new RenderPass(scene,camera));
 const ao=new GTAOPass(scene,camera,512,512);ao.blendIntensity=.7;
 ao.updateGtaoMaterial({radius:.6,distanceExponent:2,thickness:1,scale:1,samples:8});
 ao.updatePdMaterial({lumaPhi:8,depthPhi:2,normalPhi:3,radius:4});
 composer.addPass(ao);composer.addPass(new OutputPass());
 let contextVisible=true,clipping=false,assetsReady=false,contextReady=false;
 const assetStatus={sky:'loading',surroundings:'loading'};
 const getEmbedded=id=>document.getElementById(id)?.textContent.trim();
 const toBuffer=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0)).buffer;
 function applySky(texture) {
  sky=texture;sky.mapping=THREE.EquirectangularReflectionMapping;
  environmentRT.dispose();environmentRT=pmrem.fromEquirectangular(sky);
  scene.environment=environmentRT.texture;scene.background=sky;scene.backgroundIntensity=.8;
  scene.backgroundRotation.y=.5;scene.environmentRotation.y=.5;assetsReady=true;assetStatus.sky='ready';requestRender();
 }
 function failed(kind,e){assetStatus[kind]='failed';console.warn('場景素材載入失敗',kind,e?.message||e);requestRender();}
 const hdr=new HDRLoader();const embeddedSky=getEmbedded('realism-sky');
 if(embeddedSky){try{const parsed=hdr.parse(toBuffer(embeddedSky));const t=new THREE.DataTexture(parsed.data,parsed.width,parsed.height,THREE.RGBAFormat,parsed.type);t.needsUpdate=true;applySky(t);}catch(e){failed('sky',e);}}
 else hdr.load('assets/daylight.hdr?v='+revision,applySky,undefined,e=>failed('sky',e));
 const finishContext=g=>{surroundings=g.scene;surroundings.name='SURROUNDINGS';prepare(surroundings);surroundings.visible=contextVisible;scene.add(surroundings);contextReady=true;assetStatus.surroundings='ready';requestRender();};
 const loader=new GLTFLoader();const embeddedContext=getEmbedded('realism-context');
 if(embeddedContext)loader.parse(toBuffer(embeddedContext),'',finishContext,e=>failed('surroundings',e));
 else loader.load('surroundings.glb?v='+revision,finishContext,undefined,e=>failed('surroundings',e));
 function prepare(root) {
  root.traverse(o=>{
   if(!o.isMesh)return;
   const materials=Array.isArray(o.material)?o.material:[o.material];
   o.castShadow=!materials.some(m=>m.transparent);o.receiveShadow=true;
   materials.forEach(m=>{
    m.clipShadows=true;m.envMapIntensity=.85;
    for(const key of ['map','normalMap','roughnessMap','metalnessMap'])if(m[key])m[key].anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
    if(m.name?.includes('metal')){m.roughness=.32;m.metalness=.7;}
    if(m.name==='glass'){m.roughness=.08;m.metalness=.18;m.depthWrite=false;m.opacity=.22;}
    if(m.name==='ceramic')m.roughness=.19;
   });
  });
 }
 return {
  prepare,assetStatus,
  get quality(){return quality;},get ready(){return assetsReady&&contextReady;},get surroundings(){return surroundings;},
  setQuality(q){quality=q;renderer.setPixelRatio(Math.min(devicePixelRatio||1,q==='high'?2:1.25));sun.shadow.mapSize.set(q==='high'?2048:1024,q==='high'?2048:1024);if(sun.shadow.map){sun.shadow.map.dispose();sun.shadow.map=null;}requestRender();},
  setContext(v){contextVisible=v;if(surroundings)surroundings.visible=v;requestRender();},
  setClipping(v){clipping=v;},
  resize(w,h){composer.setPixelRatio(renderer.getPixelRatio());composer.setSize(w,h);},
  draw(moving=false){renderer.info.reset();if(quality==='high'&&!moving&&!clipping){composer.render();}else renderer.render(scene,camera);},
  daylight(value){sun.intensity=value==='soft'?1.2:4.2;sun.color.set(value==='warm'?0xffd3a1:0xfff0db);renderer.toneMappingExposure=value==='soft'?1.35:1.05;requestRender();},
  stats(){return {quality,assets:{...assetStatus},contextVisible,ambientOcclusion:quality==='high'&&!clipping,shadows:renderer.shadowMap.enabled,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles};}
 };
}
