import os
import re
from collections import defaultdict

def remove_comments(content):
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)
    return content

def split_import_statement(statement):
    pattern_named = re.compile(r'import\s*\{\s*(.*?)\s*\}\s*from\s*[\'"](.*?)[\'"];')
    pattern_default = re.compile(r'import\s+(\w+)\s+from\s*[\'"](.*?)[\'"];')

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
    import_statements = re.findall(r'import\s*\{.*?\}\s*from\s*[\'"].*?[\'"];|import\s+\w+\s+from\s*[\'"].*?[\'"];', content)
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
        print('  ' * depth + f'Imports from {path}: {imports}')
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
                import_statements = ', '.join([f'{original} as {alias}' for original, alias in imports])
                new_file.write(f'import {{ {import_statements} }} from "{path}";\n')

        # Write remaining content of the original file
        new_file.write(initial_content + '\n')

        # Write remaining content and other imports
        for path, imports in all_imports.items():
            if not path.startswith('@'):
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                content = remove_comments(content)
                content = re.sub(r'import\s*\{.*?\}\s*from\s*[\'"].*?[\'"];|import\s+\w+\s+from\s*[\'"].*?[\'"];', '', content)
                for original, alias in imports:
                    content = content.replace(original, alias)
                new_file.write(content + '\n')

if __name__ == '__main__':
    filepath = '/Users/rain/Downloads/OxHornCampus/entry/src/main/ets/pages/MainPage.ets'
    new_filepath = './NewMainPage.ets'
    create_new_file(filepath, new_filepath)