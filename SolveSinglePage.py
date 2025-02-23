import json
import os
import re
import shutil
from collections import defaultdict


def remove_comments(content):
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)
    return content


def split_import_statement(statement):
    pattern_named = re.compile(r'import\s*\{\s*(.*?)\s*\}\s*from\s*[\'"](.*?)[\'"]\s*;?')
    pattern_default = re.compile(r'import\s+(\w+)\s+from\s*[\'"](.*?)[\'"]\s*;?')

    match_named = pattern_named.match(statement)
    match_default = pattern_default.match(statement)

    if match_named:
        imports, path = match_named.groups()
        imports_list = imports.split(',')
        result = []
        for imp in imports_list:
            imp = imp.strip()
            if ' as ' in imp:
                original, alias = imp.split(' as ')
                result.append((original.strip(), alias.strip()))
            else:
                result.append((imp, imp))
        return result, path
    elif match_default:
        alias, path = match_default.groups()
        return [(alias, alias)], path
    return None


def parse_import_statements(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    content = remove_comments(content)
    import_statements = re.findall(
        r'import\s*\{[^}]*\}\s*from\s*[\'"][^\'"]*[\'"]|import\s+\w+\s+from\s*[\'"][^\'"]*[\'"]', content)
    parsed_imports = []
    for statement in import_statements:
        parsed_import = split_import_statement(statement)
        if parsed_import:
            parsed_imports.append(parsed_import)
            content = content.replace(statement, '')
    return parsed_imports, content


def recursive_imports(filepath, initial_file, depth=0):
    parsed_imports, remaining_content = parse_import_statements(filepath)
    all_imports = defaultdict(set)

    for imports, path in parsed_imports:
        if not path.startswith('@'):
            path = os.path.abspath(os.path.join(os.path.dirname(filepath), path + '.ets'))
        # print('  ' * depth + f'Imports from {path}: {imports}')
        if not path.startswith('@') and os.path.exists(path):
            nested_imports = recursive_imports(path, initial_file, depth + 1)
            for key, value in nested_imports.items():
                all_imports[key].update(value)
        all_imports[path].update(imports)

    return {key: list(value) for key, value in all_imports.items()}


def sloveFile(filepath, initial_file, original_name, alias_name):
    initial_dir = os.path.dirname(os.path.abspath(initial_file))
    absolute_filepath = os.path.join(initial_dir, filepath + '.ets')

    with open(absolute_filepath, 'r', encoding='utf-8') as file:
        content = file.readlines()

    line_index = -1
    pattern = re.compile(rf'\b{re.escape(original_name)}\b')
    for i, line in enumerate(content):
        if pattern.search(line):
            line_index = i
            break

    if line_index == -1:
        print(f"Original name '{original_name}' not found in the file.")
        return

    start_index = line_index
    while start_index > 0 and content[start_index].strip().startswith('@'):
        start_index -= 1

    first_char = None
    for char in content[line_index]:
        if char in '{[':
            first_char = char
            break

    if not first_char:
        print("No opening brace found after the original name.")
        return

    if first_char == '{':
        open_brace, close_brace = '{', '}'
    else:
        open_brace, close_brace = '[', ']'

    brace_count = 0
    start_brace_found = False
    end_index = line_index

    while end_index < len(content):
        brace_count += content[end_index].count(open_brace)
        brace_count -= content[end_index].count(close_brace)
        if open_brace in content[end_index]:
            start_brace_found = True
        if start_brace_found and brace_count == 0:
            break
        end_index += 1

    matched_content = ''.join(content[start_index:end_index + 1])
    replaced_content = matched_content.replace(original_name, alias_name)
    print(replaced_content)

    return replaced_content


def create_new_file(filepath, new_filepath):
    parsed_imports, initial_content = parse_import_statements(filepath)
    all_imports = recursive_imports(filepath, filepath)
    for path, imports in all_imports.items():
        print(f'Imports from {path}: {imports}')

    with open(new_filepath, 'w', encoding='utf-8') as new_file:
        # Write @ imports at the beginning
        for path, imports in all_imports.items():
            if path.startswith('@'):
                import_statements = ', '.join([original for original, alias in imports])
                new_file.write(f'import {import_statements} from "{path}";\n')

        # Write remaining content of the original file
        new_file.write(initial_content + '\n')

        # Write remaining content and other imports
        for path, imports in all_imports.items():
            if not path.startswith('@'):
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                content = remove_comments(content)
                content = re.sub(r'import\s*\{.*?\}\s*from\s*[\'"].*?[\'"];|import\s+\w+\s+from\s*[\'"].*?[\'"];', '',
                                 content)
                for original, alias in imports:
                    content = content.replace(original, alias)
                new_file.write(content + '\n')


def matchResource(filepath,new_filepath,foldername):
    #将filepath按/拆
    filepaths = filepath.split('/')
    #获取Resource的路径
    ResourcePath = '/'
    for item in filepaths:
        if item == 'main':
            ResourcePath +=item
            break
        elif item == '':
            pass
        else:
            ResourcePath+=item
            ResourcePath+='/'
    ResourcePath+='/resources/base'

    #读取new_filepath内容作为text
    with open(new_filepath, 'r', encoding='utf-8') as file:
        text = file.read()
    # 正则表达式
    pattern = r"\$r\('([^']+)'\)"

    # 查找所有匹配项
    matches = re.findall(pattern, text)

    # 输出匹配项
    for match in matches:
        #将match以.来分割
        parts = match.split('.')
        print("寻找"+match+"对应资源")
        if parts[1] == 'media':
            absolutePath = ResourcePath+'/media'
            print(f"打开{absolutePath}")
            for root, dirs, files in os.walk(absolutePath):
                for file in files:
                    if file.startswith(parts[2]):
                        source_file = os.path.join(root, file)
                        destination_file = os.path.join(foldername, file)
                        shutil.copy(source_file, destination_file)
                        print(f"拷贝 {source_file} 至 {destination_file}")
                        print("-"*20)
            #然后将原文中这一段替换为复制过去的图片的绝对路径
            #TODO： 暂时不替换，chy哪里会将需要的图片复制过去
        elif parts[1] == 'string':
            absolutePath = ResourcePath + '/element/string.json'
            print(f"打开{absolutePath}")
            with open(absolutePath, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                for item in data['string']:
                    if item['name'] == parts[2]:
                        print("找到对应value: "+item['value'])
                        text = text.replace(f"$r('{match}')", '"'+item['value']+'"')
                        print("替换成功")
                        print("-" * 20)
        elif parts[1] == 'color':
            absolutePath = ResourcePath + '/element/color.json'
            print(f"打开{absolutePath}")
            with open(absolutePath, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                for item in data['color']:
                    if item['name'] == parts[2]:
                        print("找到对应value: "+item['value'])
                        text = text.replace(f"$r('{match}')", '"'+item['value']+'"')
                        print("替换成功")
                        print("-" * 20)
        # 清空文件内容
        with open(new_filepath, 'w', encoding='utf-8') as file:
            file.write('')

        # 将修改后的内容写回 new_filepath 文件
        with open(new_filepath, 'w', encoding='utf-8') as file:
            file.write(text)





if __name__ == '__main__':
    #需要转换的page绝对路径
    filepath = ''
    # 根据filepath的最后一个文件名创建一个文件夹
    filepath_parts = filepath.split('/')
    folder_name = filepath_parts[-1].split('.')[0]
    # 创建名为folder_name的文件夹
    os.makedirs(folder_name, exist_ok=True)  # Create a folder named folder_name
    print(f"创建文件夹: {folder_name}")
    new_filepath = './' + f"{folder_name}" + '/' + filepath_parts[-1]
    print("创建文件夹成功")
    print("-" * 20)
    print(f"整合页面:{new_filepath}")
    create_new_file(filepath, new_filepath)
    print("新页面创建成功")
    print("-" * 20)
    print("修改资源")
    matchResource(filepath,new_filepath,folder_name)
