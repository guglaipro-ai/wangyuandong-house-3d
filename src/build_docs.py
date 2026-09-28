"""Reference page for real-world data, and the four-scheme design page.
Numbers are read from the built manifests so the pages cannot drift from the model."""
import json, html
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'output'
m = json.loads((OUT / 'model-manifest.json').read_text(encoding='utf-8'))
f = json.loads((OUT / 'styles/furniture-manifest.json').read_text(encoding='utf-8'))
walk = json.loads((OUT / 'walk/walk-validation.json').read_text(encoding='utf-8')) if (OUT / 'walk/walk-validation.json').exists() else {}
rd = m.get('real_details', {})
E = html.escape
CSS = ('body{margin:0;background:#f2f1ec;color:#28312d;font:16px/1.8 system-ui,"Microsoft JhengHei",sans-serif}main{max-width:1060px;margin:auto;padding:28px 18px}'
       'h1{font-size:26px;line-height:1.35}h2{font-size:20px;margin-top:34px}a{color:#315d50}.t{overflow-x:auto}table{width:100%;border-collapse:collapse;background:#fff}'
       'td,th{border-bottom:1px solid #d6d6cc;padding:9px 10px;text-align:left;vertical-align:top}th{background:#e4ebe3}.note{background:#fff8e7;border-left:4px solid #b49c57;padding:12px 16px}'
       '.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}figure{margin:0}img{width:100%;display:block;border-radius:6px}figcaption{font-size:13px;color:#57665e}'
       'small{color:#5d6b63}.pill{display:inline-block;border:1px solid #c8d1c6;border-radius:12px;padding:0 8px;font-size:13px;margin:2px}')

SRC = {
    'pdf': ('王源東住宅新建工程(請照) PDF', None),
    'law': ('建築技術規則建築設計施工編（全國法規資料庫）', 'https://law.moj.gov.tw/LawClass/LawParaDeatil.aspx?pcode=D0070115&bp=9'),
    'law2': ('建築技術規則第33～39條 樓梯、欄杆（LawPlayer 整理）', 'https://lawplayer.com/act/6437d09ce800e5f0b9301eae/8'),
    'tile': ('二丁掛尺寸 60×227 mm、外牆溝縫 5 mm（100室內設計）', 'https://www.100.com.tw/article/10643'),
    'bed1': ('台灣床墊尺寸 3尺／5尺 152×188／6尺 182×188（Emma）', 'https://www.emma-sleep.com.tw/blogs/mattress-size-guide/'),
    'bed2': ('台灣床墊尺寸指南（大漢）', 'https://www.tahan.com.tw/blog/taiwan-bed-size-dimensions-guide/'),
    'kit1': ('廚房類型與尺寸：檯面 85 cm、吊櫃距檯面 60–70 cm（100室內設計）', 'https://www.100.com.tw/article/7680'),
    'kit2': ('抽油煙機距爐面 65–75 cm（陽光空間精品廚具）', 'https://www.sunnyspacedesign.com/article_d.php?lang=tw&tb=2&id=390'),
    'kit3': ('廚具深度 60 cm 與走道（陽光空間精品廚具）', 'https://www.sunnyspacedesign.com/article_d.php?lang=tw&tb=2&id=290'),
    'elec': ('插座離地約 30 cm、開關 120 cm（100室內設計）', 'https://www.100.com.tw/v2/article/2541'),
    'elec2': ('居家插座與開關設計原則（信義居家）', 'https://livinglife.com.tw/article/doc_5409'),
    'ac': ('分離式冷氣室內機上方預留約 15 cm', 'https://aircondition.hkpro.tw/news-info.asp?id=689'),
    'furn': ('餐桌 75 cm、餐椅座高 45–50 cm（H&D 東稻家居）', 'https://www.hdlife.com.tw/Articles/Detail/502'),
    'furn2': ('茶几高度 35–60 cm 實測（設計家 Searchome）', 'https://www.searchome.net/article.aspx?id=72075'),
    'eye': ('成人站姿眼高（CityU 人體計測 Eye height）', 'http://personal.cityu.edu.hk/meachan/Online%20Anthropometry/Chapter2/Ch2-2.htm'),
    'eye2': ('平均站姿眼高 152–157 cm（Wellfr）', 'https://wellfr.com/how-tall-is-the-average-eye'),
    'ph': ('Poly Haven CC0 掃描材質', 'https://polyhaven.com/license'),
}


def cite(*keys):
    out = []
    for k in keys:
        name, url = SRC[k]
        out.append(f'<a href="{url}" target="_blank" rel="noopener">{E(name)}</a>' if url else E(name))
    return '<br>'.join(out)


rows = [
    ('外牆面材', 'PDF p8 註1「牆面材料面貼二丁掛磚」、p20 W038 牆面：磁磚 10 mm＋水泥砂漿 15 mm＋RC 18 cm', '外牆朝外面逐面改為 227×60 mm 二丁掛、5 mm 溝縫、交丁排列；室內面維持塗裝', cite('pdf', 'tile')),
    ('陽台欄杆', 'PDF p8 註2「垂直欄杆間距 <10 cm，背襯強化玻璃」；技術規則第38條 ≥110 cm', '原 3 cm 方管保留，後方加 10 mm 強化玻璃；扶手高 120 cm', cite('pdf', 'law', 'law2')),
    ('樓梯', 'PDF p20 級高 15.56–15.71 cm、級深 24 cm；規則 級高 ≤20、級深 ≥21', '逐階加 4 cm 金屬止滑條；漫遊時可實際上下樓', cite('pdf', 'law2')),
    ('屋頂', 'PDF p20 R022：輕質混凝土 5 cm＋PU 保溫板 4 cm＋PU 防水；東北立面屋突爬梯', '加入屋突爬梯、4 處落水頭、2 支 10 cm 落水管；不鏽鋼水塔依台灣常見做法補建（圖面未繪，屬假設）', cite('pdf')),
    ('踢腳板', '一般室內裝修 8 cm', f"乾區牆面共 {rd.get('skirting_m', 0):.0f} m，門口處斷開", '裝修慣例'),
    ('天花與崁燈', '平頂塗裝；崁燈約 1.8 m 間距', f"{rd.get('ceiling_m2', 0):.0f} m² 天花、{rd.get('downlights', 0)} 盞崁燈；剖切／單層俯視時自動隱藏", '裝修慣例'),
    ('開關插座', '開關約 120 cm、插座約 30 cm', f"{rd.get('switches', 0)} 個開關（門把側）、{rd.get('outlets', 0)} 組插座", cite('elec', 'elec2')),
    ('冷氣', '分離式室內機約 80×22×29 cm，上方留 10–20 cm', f"{rd.get('ac_indoor', 0)} 台室內機（頂距天花 15 cm）、{rd.get('ac_outdoor', 0)} 台室外機（四樓露台與屋頂，含基座）", cite('ac')),
    ('門窗收邊', '室內窗台板、門框飾條', f"{rd.get('window_sills', 0)} 處窗台板（2.5 cm）、{rd.get('architraves', 0)} 組門框飾條（6 cm）；室內門改為全開 90° 以便通行", '裝修慣例'),
    ('衛浴', '洗手台上方鏡', f"{rd.get('mirrors', 0)} 面鏡子；濕區牆面改為 30×60 cm 釉面磚、地坪 30×30 cm 止滑磚", '裝修慣例'),
    ('玄關', '門燈、電錶箱、信箱、門廊照明', '大門兩側壁燈、電錶箱、信箱、門廊 3 盞崁燈', '裝修慣例'),
    ('地坪', '台灣住宅常見 60×60 cm 拋光石英磚', '原始空屋的乾區地坪改為 60×60 cm、2 mm 縫', '市場常見規格'),
    ('床與家具尺寸', '台灣床墊 5 尺 152×188、6 尺 182×188、3.5 尺 105×188；餐桌 75 cm；座高 42–45 cm', '四套風格床組依床墊實尺寸再加床框；餐桌、座椅、茶几依常用高度', cite('bed1', 'bed2', 'furn', 'furn2')),
    ('廚房', '檯面 85 cm、深 60 cm；吊櫃距檯面 60–70 cm；抽油煙機距爐面 65–75 cm', '四套廚房皆採 85 cm 檯面、60 cm 深、吊櫃離檯面 65 cm、油煙機離爐面 70 cm', cite('kit1', 'kit2', 'kit3')),
    ('家具邊緣與光影', '實際家具邊角有倒角／圓角，布料有絨光，拋光磚與漆面有清漆反射', '家具方塊邊緣 7 mm 倒角；法線以 35° 為界區分硬邊與曲面；絨布與皮革加光澤層（sheen），石英磚、人字拼、大理石、朱漆加清漆層（clearcoat）；漫遊時依所在房間點亮天花燈（約 3000 K 暖光）', '材質物理常識'),
    ('手機載入', '手機 GPU 記憶體有限', '同一張貼圖只保留一份（原本最多重複 81 張）；手機自動改用 512 px 貼圖、無切線資料的輕量模型，周邊在住宅顯示後才下載', '效能'),
    ('漫遊視高', '身高 170 cm；成人眼高約比身高低 11–12 cm', '第一人稱眼高 158 cm；可跨越 25 cm 以下高差（樓梯、台階、榻榻米），茶几與床不可踩上；碰撞半徑 22 cm', cite('eye', 'eye2')),
]
table = ''.join(f'<tr><td>{E(a)}</td><td>{E(b)}</td><td>{E(c)}</td><td><small>{d}</small></td></tr>' for a, b, c, d in rows)
page = f'''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>真實構造與尺寸依據</title><style>{CSS}</style><main>
<a href="../index.html">← 回到住宅模型</a><h1>真實構造與尺寸依據</h1>
<p>更新：2026 年 9 月 28 日（台灣時間）。以下每一項都已實際建成三維幾何或材質；優先採請照圖明示內容，圖面未規定處採台灣住宅常用規格並列出查證來源。</p>
<div class="note">仍是概念展示模型：水電、冷氣與水塔位置為示意配置，不是機電設計；二丁掛顏色未於圖面指定，沿用已確認的淺灰白。未取得 CAD／現場丈量。</div>
<h2>構造與設備對照</h2><div class="t"><table><tr><th>項目</th><th>真實資料</th><th>模型中的做法</th><th>來源</th></tr>{table}</table></div>
<h2>材質貼圖</h2><p>二丁掛、石英磚、衛浴磚、陶磚、人字拼、寬版木地板、地鐵磚、摩洛哥磚、棋盤磚、藤編與清水模板紋均依實際模組尺寸程序生成（無外部圖片），UV 以公尺對應，例如二丁掛每 0.928 m 橫向 4 塊、每 1.04 m 16 皮。木紋、布料、皮革、灰泥、混凝土、紅磚沿用 {cite('ph')}。</p>
<h2>漫遊驗證</h2><p>{'已通過' if walk.get('passed') else '待執行'}：入口台階、牆面碰撞、一樓→二樓爬梯、四種風格切換中持續漫遊、家具阻擋、手機搖桿與觸控轉頭。詳見 <a href="../walk/walk-validation.json">walk-validation.json</a>。未在實體安卓手機驗收。</p>
</main></html>'''
(OUT / 'realism/references.html').write_text(page, encoding='utf-8')

# Eye-level screenshots as JPEG keep the delivery archive under GitHub's 100 MB limit.
import sys; sys.path.insert(0, str(ROOT / '.deps'))
from PIL import Image
for png in (OUT / 'walk').glob('*.png'):
    Image.open(png).convert('RGB').save(png.with_suffix('.jpg'), quality=84, optimize=True); png.unlink()

# ---- four schemes page ----
labels = {'concept': '概念', 'floor': '地坪', 'walls': '牆面', 'ceiling': '天花', 'lighting': '燈具', 'windows': '窗飾', 'signature': '代表家具'}
cards = []
for key, s in f['styles'].items():
    d = s['design']
    spec = ''.join(f'<tr><th>{labels[k]}</th><td>{E(v)}</td></tr>' for k, v in d.items())
    names = sorted({i['name'] for i in s['items'] if i['major']})
    shots = ''.join(f'<figure><a href="../walk/{key}-{v}.jpg"><img loading="lazy" src="../walk/{key}-{v}.jpg" alt="{E(s["label"])} {t}"></a><figcaption>{t}（170 cm 視角）</figcaption></figure>'
                    for v, t in (('living2', '二樓客廳'), ('kitchen', '二樓廚房'), ('gallery1', '一樓展覽／教室'), ('terrace', '四樓露台')))
    cards.append(f'<h2>{E(s["label"])}</h2><div class="t"><table>{spec}<tr><th>件數</th><td>{s["furnitureCount"]} 件主要家具、共 {s["itemCount"]} 項（含燈具、織品與器物）</td></tr></table></div>'
                 f'<p>{"".join(f"<span class=pill>{E(n)}</span>" for n in names)}</p><div class="cards">{shots}</div>')
uniq = f['distinctness']['unique_item_names']; shared = f['distinctness']['item_names_shared_by_all_four']
page = f'''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>四套風格細部規劃</title><style>{CSS}</style><main>
<a href="../index.html">← 回到住宅模型</a><h1>四套風格細部規劃</h1>
<p>四套方案各自重新規劃地坪、牆面、天花、燈具、窗飾、家具造型與擺位，而不是同一組家具換色。房間用途依先前確認：一樓展覽／教室與 Lobby、二樓客餐廳與廚房、三樓佛廳、四樓儲藏間與露台；2F／3F 臥室一床頭朝 +Y 的指定保留。</p>
<p>家具名稱比較：四套共用的名稱只有 {len(shared)} 種（{E('、'.join(shared)) or '無'}）；各套獨有名稱：{'、'.join(f"{f['styles'][k]['label']} {v} 種" for k, v in uniq.items())}。31 處門口 1.2 m 淨空與 90° 開門範圍四套皆無家具侵入。</p>
{''.join(cards)}
<p><small>家具、燈具與藝術品是概念提案，不是指定品牌或採購清單；截圖為瀏覽器即時算圖。</small></p></main></html>'''
(OUT / 'styles/design.html').write_text(page, encoding='utf-8')
print('docs written')
