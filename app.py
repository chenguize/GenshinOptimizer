from fasthtml.common import *
import json
import os
from starlette.responses import RedirectResponse

# 数据路径
DATA_PATH = "data/rules/characters.json"

# --- 中文映射字典 ---
SKILL_TYPE_MAP = {
    "NormalAttack": "普通攻击",
    "ChargedAttack": "重击",
    "PlungingAttack": "下落攻击",
    "ElementalSkill": "元素战技 (E)",
    "ElementalBurst": "元素爆发 (Q)"
}

ELEMENT_MAP = {
    "Physical": "物理",
    "Pyro": "火",
    "Hydro": "水",
    "Electro": "雷",
    "Cryo": "冰",
    "Dendro": "草",
    "Anemo": "风",
    "Geo": "岩",
    "null": "无限制"
}

REACTION_MAP = {
    "": "无反应",
    "vaporize_hydro": "蒸发 (水打火)",
    "vaporize_pyro": "蒸发 (火打水)",
    "melt_pyro": "融化 (火打冰)",
    "melt_cryo": "融化 (冰打火)",
    "aggravate": "超激化",
    "spread": "蔓激化"
}

DAMAGE_TYPE_MAP = {
    "attack": "普通攻击伤害",
    "Charged": "重击伤害",
    "plunging": "下落攻击伤害",
    "Skill": "元素战技伤害",
    "Burst": "元素爆发伤害"
}

BUFF_TYPE_MAP = [
    ("damage_bonus", "伤害加成"), ("elemental_bonus", "元素伤害加成"),
    ("atk_percent", "攻击力%"), ("hp_percent", "生命值%"),
    ("crit_rate", "暴击率"), ("crit_dmg", "暴击伤害"),
    ("em", "元素精通"), ("def_reduction", "防御削弱"),
    ("resistance_percent", "抗性降低"), ("burst_bonus", "大招加成"),
    ("skill_bonus", "战技加成"), ("charged_bonus", "重击加成"),
    ("attack_bonus", "普攻加成"), ("plunging_bonus", "下落加成"),("base_multiplier_add","固定增伤")
]


# --- 数据操作 ---
def load_characters():
    if not os.path.exists(DATA_PATH): return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_characters(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


skill_types = list(SKILL_TYPE_MAP.keys())
elements = ["Physical", "Pyro", "Hydro", "Electro", "Cryo", "Dendro", "Anemo", "Geo"]
damage_types = list(DAMAGE_TYPE_MAP.keys())
reactions = [None, "vaporize_hydro", "vaporize_pyro", "melt_pyro", "melt_cryo", "aggravate", "spread"]


def get_character_options():
    chars = load_characters()
    opts = []
    for cid, data in chars.items():
        elems = data.get("base_stats", {}).get("elements", [])
        if elems: opts.append((cid, f"{cid} ({ELEMENT_MAP.get(elems[0], elems[0])})"))
    return opts


def get_character_options_with_empty():
    return [('', '（无）')] + get_character_options()


# --- 关键：CSS 样式优化 ---
custom_assets = Div(
    Style("""
        .multiplier-row { display: grid; grid-template-columns: 1fr 1fr 60px; gap: 10px; align-items: end; margin-bottom: 8px; }
        .buff-row { display: grid; grid-template-columns: 2fr 1fr 1fr 1.5fr 60px; gap: 10px; align-items: end; margin-bottom: 10px; }
        .remove-btn { background: #ff4444; color: white; border: none; border-radius: 4px; cursor: pointer; padding: 5px 10px; }
        .add-btn { background: #00aa00; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; }
        details { margin-bottom: 20px; border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: #fafafa; }
        summary { font-weight: bold; cursor: pointer; font-size: 1.1em; }
        .success-alert { background:#d4edda; color:#155724; padding:15px; border-radius:6px; margin:20px 0; border:1px solid #c3e6cb; }

        /* 针对元素勾选框的布局重写 */
        .element-selection-grid { 
            display: flex; 
            flex-wrap: wrap; 
            gap: 20px; 
            background: #ffffff; 
            padding: 1.25rem; 
            border: 1px solid #e0e0e0; 
            border-radius: 8px;
            margin-bottom: 2rem;
        }
        .element-checkbox-wrapper { 
            display: flex; 
            align-items: center; 
            gap: 8px; 
            margin-bottom: 0 !important;
            cursor: pointer;
            min-width: 80px; /* 保证中文文字不会被换行 */
        }
        .element-checkbox-wrapper input[type="checkbox"] { 
            margin-bottom: 0 !important; 
            width: 1.2rem; 
            height: 1.2rem; 
        }

        .stats-group { margin-top: 1rem; }
    """),
    Script("""
        // 动态添加倍率和Buff的逻辑保持原样
        function createSelect(options, name) {
            const sel = document.createElement('select');
            sel.name = name;
            options.forEach(o => {
                const opt = document.createElement('option');
                opt.value = o.value; opt.textContent = o.text;
                sel.appendChild(opt);
            });
            return sel;
        }

        function addMultiplier(skill) {
            const container = document.getElementById(skill + '_multipliers');
            if (!container) return;
            const index = container.children.length;
            const row = document.createElement('div');
            row.className = 'multiplier-row';
            row.appendChild(createSelect([{value:'atk_percent',text:'攻击力%'},{value:'hp_percent',text:'生命值%'},{value:'def_percent',text:'防御力%'},{value:'em',text:'元素精通'}], skill + '_mult_type_' + index));
            const valInput = document.createElement('input');
            valInput.type = 'number'; valInput.step = '0.01'; valInput.name = skill + '_mult_value_' + index; valInput.value = '0';
            row.appendChild(valInput);
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button'; removeBtn.className = 'remove-btn'; removeBtn.textContent = '－';
            removeBtn.onclick = () => row.remove();
            row.appendChild(removeBtn);
            container.appendChild(row);
        }

        function addBuff() {
            const container = document.getElementById('buffs_container');
            if (!container) return;
            const index = container.children.length;
            const row = document.createElement('div');
            row.className = 'buff-row';
            row.appendChild(createSelect([
                {value:'damage_bonus',text:'伤害加成'},{value:'elemental_bonus',text:'元素伤害加成'},
                {value:'atk_percent',text:'攻击力%'},{value:'hp_percent',text:'生命值%'},
                {value:'crit_rate',text:'暴击率'},{value:'crit_dmg',text:'暴击伤害'},
                {value:'em',text:'元素精通'},{value:'def_reduction',text:'防御削弱'},
                {value:'resistance_percent',text:'抗性降低'},{value:'burst_bonus',text:'大招加成'},
                {value:'skill_bonus',text:'战技加成'},{value:'charged_bonus',text:'重击加成'},
                {value:'attack_bonus',text:'普攻加成'},{value:'plunging_bonus',text:'下落加成'},{value:'base_multiplier_add',text:'固定增伤'}
            ], 'buff_type_' + index));
            const valInput = document.createElement('input');
            valInput.type = 'number'; valInput.step = '0.01'; valInput.name = 'buff_value_' + index; valInput.value = '0';
            row.appendChild(valInput);
            row.appendChild(createSelect([{value:'self',text:'自身'},{value:'team',text:'队伍'}], 'buff_scope_' + index));
            row.appendChild(createSelect([
                {value:'null',text:'无限制'},{value:'Physical',text:'物理'},{value:'Pyro',text:'火'},
                {value:'Hydro',text:'水'},{value:'Electro',text:'雷'},{value:'Cryo',text:'冰'},
                {value:'Dendro',text:'草'},{value:'Anemo',text:'风'},{value:'Geo',text:'岩'}
            ], 'buff_element_' + index));
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button'; removeBtn.className = 'remove-btn'; removeBtn.textContent = '－';
            removeBtn.onclick = () => row.remove();
            row.appendChild(removeBtn);
            container.appendChild(row);
        }
    """)
)

app, rt = fast_app(pico=True, hdrs=(
    Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.amber.min.css'), custom_assets))


# --- 路由逻辑保持一致 ---
@rt("/")
def get():
    char_opts = get_character_options()
    char_opts_empty = get_character_options_with_empty()
    return Titled("原神伤害计算器 🎮",
                  A("编辑配置", href="/edit_config", cls="button",
                    style="position: absolute; top: 20px; right: 20px; background:#ff8c00; color:white;"),
                  Div(H2("角色与队伍配置", cls="text-center"),
                      Form(
                          Grid(Div(Label("主C角色:"),
                                   Select(*[Option(label, value=cid) for cid, label in char_opts], name="target_char",
                                          required=True)),
                               Div(Label("队友1 (可选):"),
                                   Select(*[Option(label, value=cid) for cid, label in char_opts_empty],
                                          name="teammate1"))),
                          Grid(Div(Label("队友2 (可选):"),
                                   Select(*[Option(label, value=cid) for cid, label in char_opts_empty],
                                          name="teammate2")),
                               Div(Label("队友3 (可选):"),
                                   Select(*[Option(label, value=cid) for cid, label in char_opts_empty],
                                          name="teammate3"))),
                          Grid(Div(Label("技能类型:"),
                                   Select(*[Option(SKILL_TYPE_MAP[st], value=st) for st in skill_types],
                                          name="skill_type", value="ElementalSkill")),
                               Div(Label("元素反应:"), Select(
                                   *[Option(REACTION_MAP.get(r or "", "无反应"), value=r or "") for r in reactions],
                                   name="reaction"))),
                          Button("计算伤害", type="submit", cls="primary", style="width: 100%; margin-top: 20px;"),
                          action="/result", method="post", cls="card"),
                      style="max-width: 900px; margin: 60px auto; padding: 20px;"))


@rt("/result", methods=["POST"])
async def post(req):
    form = await req.form()
    target_char = form.get("target_char")
    teammates = [form.get(f"teammate{i}") for i in range(1, 4) if form.get(f"teammate{i}")]
    skill_type, reaction = form.get("skill_type", "ElementalSkill"), form.get("reaction") or None
    try:
        from main import run_optimizer
        import io, sys
        old = sys.stdout
        sys.stdout = cap = io.StringIO()
        run_optimizer(target_char, teammates, skill_type=skill_type, reaction=reaction)
        output = cap.getvalue()
    except Exception as e:
        output = f"计算出错：{e}"
    finally:
        sys.stdout = old
    return Titled("优化结果", Div(H3("计算结果"), Pre(output,
                                                      style="background:#f8f9fa;padding:20px;border-radius:8px;overflow-x:auto;"),
                                  A("← 返回修改", href="/", cls="button secondary mt-3"), cls="card",
                                  style="max-width:1000px;margin:40px auto;"))


@rt("/edit_config")
def get(selected_char: str = "", saved: str = "0", new: str = "0"):
    chars = load_characters()
    char_list = list(chars.keys())
    is_new = new == "1"
    if is_new:
        selected_char, char_data = "", {"base_stats": {}, "skills": {}, "buffs": []}
    else:
        if not selected_char and char_list: selected_char = char_list[0]
        char_data = chars.get(selected_char, {"base_stats": {}, "skills": {}, "buffs": []})

    base = char_data.get("base_stats", {})
    current_elements = base.get("elements", [])
    alert = Div("✅ 修改已成功保存！", cls="success-alert") if saved == "1" else None

    # 构建表单内容
    form_items = [alert] if alert else []
    form_items += [
        H3("新建角色" if is_new else f"编辑角色：{selected_char}", cls="text-center mt-4"),
        Input(type="hidden", name="old_char_id", value=selected_char),
        Label("角色 ID (支持改名)"),
        Input(type="text", name="char_id", value=selected_char, required=True),

        # 重点优化：元素多选区
        Label("角色元素（可多选）"),
        Div(*[Label(Input(type="checkbox", name="elements", value=e, checked=(e in current_elements)),
                    f" {ELEMENT_MAP[e]}", cls="element-checkbox-wrapper") for e in elements],
            cls="element-selection-grid"),

        # 基础数值：分两组 Grid 保证宽度
        Div(
            Grid(
                Div(Label("基础攻击力"), Input(type="number", name="atk", value=base.get("atk", 300))),
                Div(Label("基础生命值"), Input(type="number", name="hp", value=base.get("hp", 12000))),
                Div(Label("基础防御力"), Input(type="number", name="def", value=base.get("def", 700)))
            ),
            Grid(
                Div(Label("暴击率"),
                    Input(type="number", step="0.01", name="crit_rate", value=base.get("crit_rate", 0.05))),
                Div(Label("暴击伤害"),
                    Input(type="number", step="0.01", name="crit_dmg", value=base.get("crit_dmg", 0.5))),
                Div(Label("元素精通"), Input(type="number", name="em", value=base.get("em", 0)))
            ),
            cls="stats-group"
        ),
        Hr(), H4("技能配置")
    ]

    # 技能配置和 Buff 部分（保持不变，逻辑已在之前调优）
    skills = char_data.get("skills", {})
    for sn in skill_types:
        info = skills.get(sn, {}).get("default", {})
        rows = [Div(Select(*[Option(t, value=v, selected=(m.get("type") == v)) for t, v in
                             [("攻击力%", "atk_percent"), ("生命值%", "hp_percent"), ("防御力%", "def_percent"),
                              ("元素精通", "em")]], name=f"{sn}_mult_type_{i}"),
                    Input(type="number", step="0.01", name=f"{sn}_mult_value_{i}", value=m.get("value", 0)),
                    Button("－", type="button", cls="remove-btn", onclick="this.parentElement.remove()"),
                    cls="multiplier-row") for i, m in enumerate(info.get("multipliers", []))]

        form_items += [Details(Summary(SKILL_TYPE_MAP[sn]),
                               Grid(Div(Label("元素"), Select(
                                   *[Option(ELEMENT_MAP[e], value=e, selected=(e == info.get("element", "Physical")))
                                     for e in elements], name=f"{sn}_element")),
                                    Div(Label("伤害类型"), Select(*[Option(DAMAGE_TYPE_MAP[d], value=d, selected=(
                                                d == info.get("damage_type", "Skill"))) for d in damage_types],
                                                                  name=f"{sn}_damage_type"))),
                               Div(*rows, id=f"{sn}_multipliers"),
                               Button("＋ 添加倍率", type="button", cls="add-btn", onclick=f"addMultiplier('{sn}')"))]

    buffs = char_data.get("buffs", [])
    form_items += [
        Hr(), H4("增益效果 (Buff)"),
        Div(id="buffs_container", *[Div(
            Select(*[Option(v, value=k, selected=(k == b.get("type"))) for k, v in BUFF_TYPE_MAP],
                   name=f"buff_type_{i}"),
            Input(type="number", step="0.01", name=f"buff_value_{i}", value=b.get("value", 0)),
            Select(Option("自身", value="self", selected=(b.get("scope") == "self")),
                   Option("队伍", value="team", selected=(b.get("scope") == "team")), name=f"buff_scope_{i}"),
            Select(*[Option(ELEMENT_MAP[e], value=e, selected=(e == b.get("element", "null"))) for e in
                     ["null"] + elements], name=f"buff_element_{i}"),
            Button("－", type="button", cls="remove-btn", onclick="this.parentElement.remove()"),
            cls="buff-row") for i, b in enumerate(buffs)]),
        Button("＋ 添加 Buff", type="button", cls="add-btn", onclick="addBuff()"),
        Hr(), Button("💾 保存角色", type="submit", cls="primary large")
    ]

    return Titled("配置管理",
                  Div(A("← 返回主页", href="/", cls="button outline"),
                      A("＋ 新建角色", href="/edit_config?new=1", cls="button", style="margin-left:10px;")),
                  Div(Select(
                      *[Option(cid, value=cid, selected=(cid == selected_char and not is_new)) for cid in char_list],
                      onchange="location.href='/edit_config?selected_char='+this.value", cls="mb-4"),
                      Form(*form_items, action="/save_config", method="post"),
                      cls="card", style="max-width:1200px; margin:20px auto; padding:30px;"))


@rt("/save_config", methods=["POST"])
async def post(req):
    form = await req.form()
    new_id, old_id = form.get("char_id", "").strip(), form.get("old_char_id", "").strip()
    if not new_id: return RedirectResponse("/edit_config", status_code=303)
    chars = load_characters()
    if old_id and old_id in chars and old_id != new_id: chars[new_id] = chars.pop(old_id)
    data = chars.setdefault(new_id, {"base_stats": {}, "skills": {}, "buffs": []})
    base = data["base_stats"]
    # 修复多选保存逻辑
    base["elements"] = [v for k, v in form.items() if k == "elements"] or ["Physical"]
    for k in ["atk", "hp", "def", "em"]: base[k] = int(form.get(k, 0))
    for k in ["crit_rate", "crit_dmg"]: base[k] = float(form.get(k, 0))
    # 技能保存逻辑
    for sn in skill_types:
        d = data["skills"].setdefault(sn, {"default": {}})["default"]
        d["element"], d["damage_type"] = form.get(f"{sn}_element", "Physical"), form.get(f"{sn}_damage_type", "Skill")
        mults, i = [], 0
        while f"{sn}_mult_type_{i}" in form:
            t, v = form.get(f"{sn}_mult_type_{i}"), form.get(f"{sn}_mult_value_{i}")
            if t and v: mults.append({"type": t, "value": float(v)})
            i += 1
        d["multipliers"] = mults
    # Buff 保存逻辑
    data["buffs"] = []
    i = 0
    while f"buff_type_{i}" in form:
        t = form.get(f"buff_type_{i}")
        if t:
            data["buffs"].append({"type": t, "value": float(form.get(f"buff_value_{i}", 0)),
                                  "scope": form.get(f"buff_scope_{i}", "self"),
                                  "element": form.get(f"buff_element_{i}", "null")})
        i += 1
    save_characters(chars)
    return RedirectResponse(f"/edit_config?selected_char={new_id}&saved=1", status_code=303)


serve()