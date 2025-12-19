# 原神全自动圣遗物遗传算法优化器  
**超详细新手指南（Ultra-Detailed Beginner Guide）**

本工具是一个基于**遗传算法**的工业级伤害模拟优化器。它能自动装配你的圣遗物、准确判定套装效果、结合角色自身天赋（Self-Buff）和队友Buff（Team-Buff），在数以亿计的组合中搜索**全局最优伤害面板**，帮助你找到角色真正的最强配装。  

适用于追求极致输出的玩家，支持复杂队伍Buff、元素反应、减抗减防等高级计算。

### 一、安装与环境准备（从零开始）

1. **安装 Python**  
   下载 Python 3.10 或更高版本（推荐 3.12）。  
   官网：https://www.python.org/downloads/  
   安装时**务必勾选 “Add Python to PATH”**（添加到环境变量）。

2. **克隆或下载项目代码**  
   - 如果你有 Git：  
     ```bash
     git clone https://github.com/chenguize/GenshinOptimizer.git

3.**安装依赖库**
安装依赖库
进入项目文件夹，运行：Bashpip install -r requirements.txt（如果没有 requirements.txt，可手动安装：pip install numpy scipy matplotlib）
4.**运行方式**
新手推荐：运行 Web 界面Bashpython app.py浏览器打开：**http://localhost:5001**（图形化操作最友好）
高级用户：python main.py


### 3. 二、核心逻辑与数据流 + 三、参数配置详解

```markdown
### 二、核心逻辑与数据流

工具分为两个阶段：  
1. **预处理阶段**：加载白字 + 合并 Self/Team Buff → 固定面板。  
2. **进化搜索阶段**：遗传算法迭代所有圣遗物组合 → 计算套装效果 + 伤害期望 → 输出最优配装。

### 三、参数配置详解（手动调参必读）

#### 1. `main.py`：战斗环境配置
- `target_char`：角色键名（如 `"leishen"` 或中文名）。  
- `skill_type`（最重要）：  
  `NormalAttack` / `ChargedAttack` / `ElementalSkill` / `ElementalBurst` / `PlungingAttack`  
- `reaction`：`vaporize_hydro`、`melt_pyro`、`aggravate`、`spread` 等。  
- `enemy_level`：默认 100  
- `resistance_percent`：减抗后抗性（如 -0.3）

#### 2. `characters.json` 示例（那维莱特 30% 水伤）
```json
{
  "type": "elemental_bonus",
  "value": 0.30,
  "element": "Hydro"
}
#### 3. `set_effects.json`：套装效果配置

此文件用于定义所有圣遗物套装的 2 件套 / 4 件套效果。  

**最重要提醒**：  
套装效果中的 `type` 字段 **必须** 与 `main.py` 中设置的 `skill_type` 严格匹配，否则角色将完全吃不到这部分加成！  

正确示例：  
- 计算**重击**伤害 → 必须使用 `charged_bonus` 或通用 `damage_bonus`  
- 计算**普攻**伤害 → 必须使用 `attack_bonus` 或通用 `damage_bonus`  
- 计算**下落攻击** → 必须使用 `plunging_bonus`  
- 计算**元素战技** → 必须使用 `skill_bonus`  

错误示例：把重击写成 `skill_bonus` → 那维莱特重击完全吃不到追忆/辰砂等套装加成。

#### 4. 关键 Buff 类型字典（严格遵守拼写！）

所有 Buff（包括角色天赋、武器效果、队伍 Buff、套装效果）中的 `type` 字段必须严格按照下表填写，**一个字母大小写或拼写错误都会导致对应乘区完全失效**。

| 乘区分类 | type 字段            | 适用场景                                      |
|----------|-----------------------|-----------------------------------------------|
| 基础区   | atk_percent          | 攻击力百分比加成（基于白字计算）             |
|          | atk_flat             | 攻击力固定值加成                              |
|          | hp_percent           | 生命值百分比加成                              |
|          | hp_flat              | 生命值固定值加成                              |
|          | em                   | 元素精通                                      |
| 增伤区   | damage_bonus         | 全伤害加成（所有技能类型通用）                |
|          | elemental_bonus      | 元素伤害加成（需额外指定 `"element": "Hydro"` 等） |
|          | charged_bonus        | 重击专属增伤（仅 skill_type = ChargedAttack 时生效） |
|          | attack_bonus         | 普攻专属增伤（仅 skill_type = NormalAttack 时生效） |
|          | plunging_bonus       | 下落攻击专属增伤（仅 skill_type = PlungingAttack 时生效） |
|          | skill_bonus          | 元素战技专属增伤（仅 skill_type = ElementalSkill 时生效） |
| 双暴区   | crit_rate            | 暴击率                                        |
|          | crit_dmg             | 暴击伤害                                      |
| 特殊区   | def_reduction        | 减防（如雷神2命、草神2命）                   |
|          | resistance_reduction | 减抗（如宗室秘境、风套4件、钟离玉璋）         |





### 4. 四、五、六 部分

```
### 四、圣遗物自动化导入（YAS + Parser）

1. 下载 YAS：https://github.com/wormtql/yas/releases  
2. 运行 yas.exe 扫描背包 → 生成 mona.json  
3. 运行项目内 `parser(yas_converter).py` → 生成 artifacts.json（保留 ID）

### 五、开发者调试建议
- 检查控制台 “[4] 队友后固定面板” 是否正确。  
- all_damage_bonus 异常 → type 与 skill_type 不匹配。  
- 圣遗物多时调高 population_size（800+）。  
- 拼写必须统一，参考上表。

### 六、快速上手建议
1. `python app.py` → http://localhost:5001  
2. 导入 artifacts.json  
3. 设置角色与技能类型  
4. 运行优化 → 查看最优配装

伤害爆表，玩得开心！![img.png](img.png)![img_1.png](img_1.png)