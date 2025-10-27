import re
import json
from typing import List, Dict, Any, Optional, Union
import html
import markdown
from markdown.extensions import Extension


class MessageFormatter:
    def __init__(self):
        self.regex_placement = {
            'MD_DISPLAY': 0,
            'USER_INPUT': 1,
            'AI_OUTPUT': 2,
            'SLASH_COMMAND': 3,
            'WORLD_INFO': 5,
            'REASONING': 6
        }
        
        self.substitute_find_regex = {
            'NONE': 0,
            'RAW': 1,
            'ESCAPED': 2
        }
        
        # 完整的正则配置
        self.regex_scripts = [
            {
                "id": "f25de40e-0c35-4014-aece-223889a37123",
                "scriptName": "【kemini】K4o添加tag修复",
                "disabled": False,
                "runOnEdit": True,
                "findRegex": "^([\\s\\S]*)$",
                "replaceString": "<interactive_input>\n$1\n</interactive_input>",
                "trimStrings": [],
                "placement": [1],
                "substituteRegex": 0,
                "minDepth": None,
                "maxDepth": 1,
                "markdownOnly": True,
                "promptOnly": True
            },
            {
                "id": "27a031e7-8063-4265-a339-c862df42eada",
                "scriptName": "【kemini】七月通用去除多余内容",
                "disabled": False,
                "runOnEdit": True,
                "findRegex": "/(<disclaimer>.*?</disclaimer>)|(<guifan>.*?</guifan>)|```start|<content>|</content>|```end|<done>|`<done>`|(<!--[\\s\\S]*?-->(\\s*))|(.*?</think(ing)?>(\\n)?)|(<think(ing)?>[\\s\\S]*<\\/think(ing)?>(\\n)?)/gs",
                "replaceString": "",
                "trimStrings": [],
                "placement": [2],
                "substituteRegex": 0,
                "minDepth": None,
                "maxDepth": None,
                "markdownOnly": True,
                "promptOnly": True
            },
            {
                "id": "65a55680-8987-4398-8bce-29e65c29cc3e",
                "scriptName": "【kemini】省略号减少",
                "disabled": False,
                "runOnEdit": True,
                "findRegex": "/([\\u4e00-\\u9fa5])(?:…|……)(\\1)|(?:…|……)/g",
                "replaceString": "$1",
                "trimStrings": [],
                "placement": [2],
                "substituteRegex": 0,
                "minDepth": None,
                "maxDepth": None,
                "markdownOnly": True,
                "promptOnly": True
            },
            {
                "id": "454301b3-f7f0-45ba-b3a2-86c06896f2fd",
                "scriptName": "【kemini】小总结1",
                "disabled": False,
                "runOnEdit": True,
                "findRegex": "/<details>\\s*<summary>\\s*摘要\\s*<\\/summary>[\\s\\S]*?<\\/details>/gsi",
                "replaceString": "",
                "trimStrings": [],
                "placement": [2],
                "substituteRegex": 0,
                "minDepth": None,
                "maxDepth": 10,
                "markdownOnly": False,
                "promptOnly": True
            },
            {
                "id": "cf4d35da-95f8-451c-9e38-d86cc750033b",
                "scriptName": "【kemini】小总结2",
                "disabled": False,
                "runOnEdit": True,
                "findRegex": "/([\\s\\S]*?<details>\\s*<summary>\\s*摘要\\s*<\\/summary>|<\\/details>[\\s\\S]*?$)/gs",
                "replaceString": "",
                "trimStrings": [],
                "placement": [2],
                "substituteRegex": 0,
                "minDepth": 11,
                "maxDepth": None,
                "markdownOnly": False,
                "promptOnly": True
            }
        ]

    def sanitize_regex_macro(self, text: str) -> str:
        """转义正则表达式中的特殊字符"""
        if not text or not isinstance(text, str):
            return text
            
        escape_map = {
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
            '\v': '\\v',
            '\f': '\\f',
            '\0': '\\0'
        }
        
        result = []
        for char in text:
            if char in escape_map:
                result.append(escape_map[char])
            elif char in '.^$*+?{}[]\\/|()':
                result.append('\\' + char)
            else:
                result.append(char)
                
        return ''.join(result)

    def substitute_params(self, text: str, character_override: Optional[str] = None) -> str:
        """参数替换函数（简化版）"""
        # 这里可以根据需要实现更复杂的参数替换逻辑
        # 目前返回原文本
        return text

    def substitute_params_extended(self, text: str, params: Dict = None, sanitize_func = None) -> str:
        """扩展参数替换函数"""
        if sanitize_func:
            return sanitize_func(text)
        return text

    def regex_from_string(self, pattern: str) -> Optional[re.Pattern]:
        """从字符串创建正则表达式"""
        try:
            # 处理 /pattern/flags 格式
            clean_pattern = pattern
            flags = 0
            
            if pattern.startswith('/') and pattern.rfind('/') > 0:
                # 找到最后一个斜杠的位置
                last_slash = pattern.rfind('/')
                clean_pattern = pattern[1:last_slash]  # 提取模式部分
                flags_str = pattern[last_slash + 1:]   # 提取标志部分
                
                # 设置正则标志
                if 's' in flags_str:
                    flags |= re.DOTALL
                if 'i' in flags_str:
                    flags |= re.IGNORECASE
                if 'g' in flags_str:
                    # Python re 默认是全局匹配，不需要特殊处理
                    pass
            else:
                # 没有斜杠包裹，使用 DOTALL 作为默认
                flags = re.DOTALL
            
            # 编译正则表达式
            compiled_regex = re.compile(clean_pattern, flags)
            return compiled_regex
            
        except re.error as e:
            print(f"Invalid regex pattern: {pattern}, error: {e}")
            return None

    def filter_string(self, raw_string: str, trim_strings: List[str], character_override: Optional[str] = None) -> str:
        """过滤需要修剪的字符串"""
        final_string = raw_string
        for trim_string in trim_strings:
            sub_trim_string = self.substitute_params(trim_string, character_override)
            final_string = final_string.replace(sub_trim_string, '')
        return final_string

    def run_regex_script(self, regex_script: Dict, raw_string: str, character_override: Optional[str] = None) -> str:
        """运行单个正则脚本 - 按照JS逻辑实现"""
        if (not regex_script or regex_script.get('disabled') or 
            not regex_script.get('findRegex') or not raw_string):
            return raw_string

        # 获取正则表达式字符串
        substitute_regex = regex_script.get('substituteRegex', 0)
        if substitute_regex == self.substitute_find_regex['NONE']:
            regex_string = regex_script['findRegex']
        elif substitute_regex == self.substitute_find_regex['RAW']:
            regex_string = self.substitute_params_extended(regex_script['findRegex'])
        elif substitute_regex == self.substitute_find_regex['ESCAPED']:
            regex_string = self.substitute_params_extended(
                regex_script['findRegex'], 
                {}, 
                self.sanitize_regex_macro
            )
        else:
            regex_string = regex_script['findRegex']

        # 编译正则表达式
        find_regex = self.regex_from_string(regex_string)
        if not find_regex:
            return raw_string

        # 执行替换 - 直接在整个字符串上匹配，就像JS那样
        def replace_function(match):
            args = list(match.groups())
            args.insert(0, match.group(0))  # 完整匹配作为 $0
            
            replace_string = regex_script['replaceString'].replace('{{match}}', '$0')
            
            # 处理分组引用
            def replace_groups(m):
                group_num = int(m.group(1))
                if group_num < len(args) and args[group_num] is not None:
                    match_text = args[group_num]
                    filtered_match = self.filter_string(
                        match_text, 
                        regex_script.get('trimStrings', []), 
                        {'characterOverride': character_override}
                    )
                    return filtered_match
                return ''
            
            replace_with_groups = re.sub(r'\$(\d+)', replace_groups, replace_string)
            return self.substitute_params(replace_with_groups)

        try:
            new_string = find_regex.sub(replace_function, raw_string)
            return new_string
        except Exception as e:
            print(f"Error running regex script {regex_script.get('scriptName')}: {e}")
            return raw_string

    def get_regexed_string(self, raw_string: str, placement: int, 
                        character_override: Optional[str] = None,
                        is_markdown: bool = False, 
                        is_prompt: bool = False,
                        is_edit: bool = False,
                        depth: Optional[int] = None,
                        character_regex_scripts: Optional[List[Dict]] = None) -> str:
        """获取经过正则处理的字符串 - 按照JS逻辑顺序执行多个脚本"""
        if not isinstance(raw_string, str):
            print('getRegexedString: rawString is not a string. Returning empty string.')
            return ''

        final_string = raw_string
        if character_regex_scripts:
            all_regex_scripts = self.regex_scripts + character_regex_scripts
        else :
            all_regex_scripts = self.regex_scripts

        # 遍历所有正则脚本，按照数组顺序执行
        for script in all_regex_scripts:
            if script.get('disabled'):
                continue
                
            # 检查 Markdown 和 Prompt 条件
            markdown_condition = (script.get('markdownOnly') and is_markdown)
            prompt_condition = (script.get('promptOnly') and is_prompt)
            general_condition = (not script.get('markdownOnly') and 
                            not script.get('promptOnly') and 
                            not is_markdown and not is_prompt)
            
            if not (markdown_condition or prompt_condition or general_condition):
                continue

            # 检查编辑条件
            if is_edit and not script.get('runOnEdit', False):
                print(f"getRegexedString: Skipping script {script.get('scriptName')} because it does not run on edit")
                continue

            # 检查深度条件
            if depth is not None:
                min_depth = script.get('minDepth')
                max_depth = script.get('maxDepth')
                
                if min_depth is not None and depth < min_depth:
                    print(f"getRegexedString: Skipping script {script.get('scriptName')} because depth {depth} is less than minDepth {min_depth}")
                    continue
                    
                if max_depth is not None and depth > max_depth:
                    print(f"getRegexedString: Skipping script {script.get('scriptName')} because depth {depth} is greater than maxDepth {max_depth}")
                    continue

            # 检查位置条件
            if placement in script.get('placement', []):
                print(f"Applying regex script: {script.get('scriptName')}")
                # 每个脚本都在前一个脚本处理结果的基础上继续处理
                final_string = self.run_regex_script(script, final_string, {
                    'characterOverride': character_override
                })

        return final_string

    def messageFormatting(self, content: str, placement: int = 2, 
                         is_markdown: bool = True, 
                         is_prompt: bool = True,
                         is_edit: bool = False,
                         depth: int = 0,
                         character_regex_scripts: Optional[List[Dict]] = None) -> str:
        """
        主要的消息格式化方法
        
        Args:
            content: 要格式化的内容
            placement: 位置类型 (2 = AI_OUTPUT)
            is_markdown: 是否是 Markdown 内容
            is_prompt: 是否是提示内容
            is_edit: 是否是编辑操作
            depth: 深度级别
            
        Returns:
            格式化后的内容
        """
        return self.get_regexed_string(
            content, 
            placement,
            is_markdown=is_markdown,
            is_prompt=is_prompt,
            is_edit=is_edit,
            depth=depth,
            character_regex_scripts = character_regex_scripts
        )



# 创建全局实例
_formatter_instance = MessageFormatter()

def format_message(content: str, placement: int = 2, 
                  is_markdown: bool = True, 
                  is_prompt: bool = True,
                  is_edit: bool = False,
                  depth: int = 0,
                  character_regex_scripts: Optional[List[Dict]] = None) -> str:
    """
    外部调用的消息格式化函数
    
    Args:
        content: 要格式化的内容
        placement: 位置类型 (1=USER_INPUT, 2=AI_OUTPUT, 等等)
        is_markdown: 是否是 Markdown 内容
        is_prompt: 是否是提示内容
        is_edit: 是否是编辑操作
        depth: 深度级别
        
    Returns:
        格式化后的内容
    """

    mes = _formatter_instance.messageFormatting(
        content=content,
        placement=placement,
        is_markdown=is_markdown,
        is_prompt=is_prompt,
        is_edit=is_edit,
        depth=depth,
        character_regex_scripts=character_regex_scripts
    )
    mes = replace_quotes(mes)
    print(mes)
    return mes


def replace_quotes(mes):
    def replacement_html(match):
            contents = match.group(1)  # 捕获 HTML 标签内容
            return f'<{contents.replace('"', '\ufffe')}>'

    mes = re.sub(r'<([^>]+)>', replacement_html, mes, flags=re.MULTILINE)


    def replacement(match):
        # 捕获组对应正则表达式中的括号组
        p1 = match.group(1)  # 英文双引号
        p2 = match.group(2)  # 花括号双引号
        p3 = match.group(3)  # 法语双角引号
        p4 = match.group(4)  # 日式角引号
        p5 = match.group(5)  # 日式白角引号
        p6 = match.group(6)  # 全角双引号

        if p1:
            # 英文双引号
            return f'<q>"{p1[1:-1]}"</q>'
        elif p2:
            # 花括号双引号 “ ”
            return f'<q>“{p2[1:-1]}”</q>'
        elif p3:
            # 法语双角引号 « »
            return f'<q>«{p3[1:-1]}»</q>'
        elif p4:
            # 日式角引号 「 」
            return f'<q>「{p4[1:-1]}」</q>'
        elif p5:
            # 日式白角引号 『 』
            return f'<q>『{p5[1:-1]}』</q>'
        elif p6:
            # 全角双引号 ＂ ＂
            return f'<q>＂{p6[1:-1]}＂</q>'
        else:
            # 返回原始匹配内容（<style> 或代码块）
            return match.group(0)

    # 正则表达式，与 JavaScript 版本一致
    pattern = r'<style>[\s\S]*?</style>|```[\s\S]*?```|~~~[\s\S]*?~~~|``[\s\S]*?``|`[\s\S]*?`|(".*?")|(\u201C.*?\u201D)|(\u00AB.*?\u00BB)|(\u300C.*?\u300D)|(\u300E.*?\u300F)|(\uFF02.*?\uFF02)'
    
    # 使用 re.sub 进行替换，flags=re.MULTILINE 对应 JavaScript 的 /m
    mes = re.sub(pattern, replacement, mes, flags=re.MULTILINE | re.IGNORECASE)

    # 还原html
    mes = mes.replace('\ufffe', '"')



    mes = mes.replace(r'\begin{align*}', '$$')
    mes = mes.replace(r'\end{align*}', '$$')

    # 2. Markdown 转 HTML
    mes = markdown.markdown(mes, extensions=['extra', 'fenced_code', 'codehilite'])

    # 3. 清理 <code> 块中的换行符
    mes = re.sub(r'<code[^>]*>[\s\S]*?</code>', lambda match: match.group(0).replace('\n', ''), mes, flags=re.MULTILINE)

    # 4. 还原 <br> 为换行符
    mes = re.sub(r'<br\s*/?>', '\n', mes, flags=re.MULTILINE | re.IGNORECASE)

    # 5. 清理首尾空白
    mes = mes.strip()

    # 6. 还原 <code> 块中的 &amp; 为 &
    mes = re.sub(r'<code[^>]*>[\s\S]*?</code>', lambda match: match.group(0).replace('&amp;', '&'), mes, flags=re.MULTILINE)


    return mes












# 使用示例
if __name__ == "__main__":
    formatter = MessageFormatter()
    
    # 测试内容
    test_content = """<thinking>
- 当前处于何种情境？
时间：南宋末年，蒙古大军围攻襄阳
地点：襄阳城墙内侧，通往南门的石阶
社会关系：pride88（民夫）正奉黄蓉之命，运送油罐至南门交给鲁有脚。与黄蓉存在临时指派关系。
角色当前姿势：抱着沉重的油罐，在石阶上飞奔。

- <interactive_input>传递了何种需求？
选择1：不顾一切，用最快速度冲向南门。表明互动者希望加快节奏，尽快抵达南门，甚至可能触发与蒙古兵的冲突。

- 为保证剧情推进，正文剧情将大体分为三段展开，每一段需在前一段的基础上有所进展，如何安排剧情？

第一段： 描写pride88为了尽快抵达南门，不顾危险，在箭雨中飞奔。
第二段： 描写pride88遭遇突发状况，例如遇到溃兵阻路，或者遇到零星的蒙古士兵。
第三段： 描写pride88克服困难，最终抵达南门，并与鲁有脚成功交接油罐。为后续南门守卫战埋下伏笔。

</thinking>

pride88咬紧牙关，抱着（黑陶油罐）加速向下冲去。石阶又陡又滑，（黑陶油罐）沉重异常，每一步都颠簸得他气血翻涌。（城墙）顶上，箭矢如雨般落下，不时有惨叫声传来，显然是（守城士兵）中箭了。

<!-- consider: (情绪模拟插入) -->
<!-- 角色最应该出现的情绪：恐惧，焦虑，害怕被箭射中，担心完不成任务 -->
<!-- 角色更平淡正面的情绪特征： 紧张， 急迫，希望能尽快完成任务，有一点点兴奋，希望能帮上忙 -->
<!-- 这里选择"更平淡正面的情绪特征"里的紧张与急迫 -->

他顾不得其他，只想着快点，再快点，*南门若破，襄阳就完了，自己也得跟着遭殃*。

<!-- consider: (对白模拟插入) -->
<!-- 此时最适合的语言： "妈的，拼了！"给自己打气，缓解恐惧 -->
<!-- 情绪特征更明显、生活化气息更突出的语言： "让开让开！别挡路！" 提醒前方的人，同时给自己壮胆 -->
<!-- 这里选择"情绪特征更明显、生活化气息更突出的语言"，更符合当前的情境和角色心理 -->
<!-- 添加此项的原因是使NPC的表现更符合人物逻辑，避免NPC过于NPC -->

"让开让开！别挡路！"

他一边跑，一边大声喊叫，希望能让前方的人避让一下。奈何此时的（城墙通道），到处都是乱窜的（士兵）和（民夫），哭喊声、叫骂声响成一片，根本听不清他在喊什么。

果然，（pride88）一不小心撞到了一个人。那人穿着（士兵的盔甲），却瘫坐在地上，面如土色，显然是受了伤。

"滚开！" 那（士兵）有气无力地骂了一句。

<!-- consider: (情绪模拟插入) -->
<!-- 角色最应该出现的情绪：愤怒， 焦急， 觉得对方挡了自己的路，耽误了时间 -->
<!-- 角色更平淡正面的情绪特征：无奈， 觉得对方也很可怜，但自己时间紧迫 -->

（pride88）也顾不上（士兵），他现在只想尽快把（油罐）送到，*时间就是生命*。

<!-- consider: (对白模拟插入) -->
<!-- 此时最适合的语言： "对不住了！" 道歉一声，然后绕过去 -->
<!-- 情绪特征更明显、生活化气息更突出的语言："借过借过！"更加简洁，符合赶时间的状态 -->

"借过借过！"他喊着，试图绕过（那士兵）。

然而，（pride88）还没跑出两步，突然脚下一绊，身子猛地向前扑去，怀里的（油罐）也脱手飞出。

"砰！"

（黑陶油罐）重重地摔在地上，发出一声闷响，虽然没有破裂，但罐口的封泥却被震开，里面的（油）撒了出来，顿时一股刺鼻的味道弥漫开来。

<!-- consider: (情绪模拟插入) -->
<!-- 角色最应该出现的情绪：绝望， 完了，这下全完了，任务失败了，襄阳也要完了 -->
<!-- 角色更平淡正面的情绪特征：懊恼，怎么这么不小心，但是事情已经发生，只能想办法补救 -->

他连忙爬起来，顾不得身上的疼痛，赶紧去捡（油罐）。

就在这时，一把低沉的声音在（pride88）的耳边响起："你是干什么的？"

他抬头一看，只见一个身材高大的（汉子）站在他面前。那（汉子）方面大耳，满脸络腮胡，穿着一件油腻腻的（皮甲），手里拿着一根（铁棒），正是（丐帮）八袋（弟子）鲁有脚。

"鲁…鲁帮主…" (pride88)结结巴巴地说道："我是黄帮主派来的，送…送（油）…"

<StatusBlock>
气血：虚弱
神识：紧张
因果：民夫 - 黄蓉（临时指派），民夫 - 鲁有脚（待建立）
声望：默默无闻
招式：-
心法：-
身法：-
奇技：-
当前地点：襄阳城墙（往南门楼途中）
行囊物品：半罐黑陶油
当前摘要：襄阳民夫路人甲，奉黄蓉之命，抱油罐急送南门城楼，途中不慎摔倒，油罐倾洒，被鲁有脚盘问。
选项1：如实禀告情况，请求鲁有脚的帮助。
选项2：隐瞒油罐倾洒之事，蒙混过关。
选项3：夺路而逃，避免被追责。
时间：淳祐十一年六月十五日未时
人名：黄蓉
服装：荆钗布裙
动作：发号施令
人名：受伤士兵
服装：士兵的盔甲
动作：瘫坐在地上
人名：鲁有脚
服装：油腻腻的皮甲
动作：手拿铁棒
</StatusBlock>"""
    
    # 格式化消息
    formatted_content = formatter.messageFormatting(
        content=test_content,
        placement=2,  # AI_OUTPUT
        is_markdown=True,
        is_prompt=True,
        is_edit=False,
        depth=0
    )
    
    print("原始内容:")
    print(test_content)
    print("\n" + "="*50 + "\n")
    print("格式化后内容:")
    print(formatted_content)