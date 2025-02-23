import os
import re


# 步骤 1: 找出两个项目中名字相同的文件（扩展名不同），包括递归子文件夹
def find_matching_files(project_dir1, project_dir2):
    print("正在扫描项目目录，寻找匹配的文件...")
    files1 = {}
    files2 = {}

    # 递归遍历第一个项目目录
    for root, _, files in os.walk(project_dir1):
        for file in files:
            filename, ext = os.path.splitext(file)
            filename = filename.lower()  # 转小写，避免大小写问题
            if filename not in files1:
                files1[filename] = []
            rel_path = os.path.relpath(root, project_dir1)
            files1[filename].append((rel_path, file))

    print(f"扫描完成：第一个项目中找到 {len(files1)} 个唯一文件名。")

    # 递归遍历第二个项目目录
    for root, _, files in os.walk(project_dir2):
        for file in files:
            filename, ext = os.path.splitext(file)
            filename = filename.lower()
            if filename not in files2:
                files2[filename] = []
            rel_path = os.path.relpath(root, project_dir2)
            files2[filename].append((rel_path, file))

    print(f"扫描完成：第二个项目中找到 {len(files2)} 个唯一文件名。")

    matching_files = []
    total_comparisons = len(files1)

    # 比较两个项目中的文件名（扩展名不同）
    print("正在匹配文件名...")
    for idx, filename in enumerate(files1, 1):
        if filename in files2:
            ts_files = [f for f in files1[filename] if f[1].endswith('.ts')]
            java_files = [f for f in files2[filename] if f[1].endswith('.java')]

            for ts_file in ts_files:
                for java_file in java_files:
                    ts_rel_path, ts_filename = ts_file
                    java_rel_path, java_filename = java_file
                    matching_files.append((ts_rel_path, java_rel_path, filename))

        # 打印匹配进度
        if idx % 100 == 0 or idx == total_comparisons:
            print(f"文件匹配进度：{idx}/{total_comparisons} 已完成。")

    print(f"文件匹配完成，共找到 {len(matching_files)} 对匹配文件。")
    return matching_files, files1, files2


# 步骤 2: 提取函数名和整个函数体
import re

def extract_functions_with_content(file_path, lang):
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # 更新后的正则表达式，确保能够正确匹配函数体
    if lang == 'ts':
        # TypeScript 函数匹配正则
        func_pattern = re.compile(
            r'(public|private|protected|static|readonly)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*(?::\s*[\w<>,\[\]]+)?\s*\{([\s\S]*?)\}',
            re.DOTALL
        )
    elif lang == 'java':
        # Java 函数匹配正则
        func_pattern = re.compile(
            r'(public|private|protected|static)?\s+[\w<>,\[\]]+\s+(\w+)\s*\([^)]*\)\s*\{([\s\S]*?)\}',
            re.DOTALL
        )

    functions = func_pattern.findall(code)

    # 输出调试信息，检查捕获的函数内容
    print(f"在文件 {file_path} 中找到 {len(functions)} 个函数：")
    for func in functions:
        print(func)

    # 防止越界错误：只返回有效的元组
    return [(func[1], func[0] + " " + func[1] + " (" + func[2] + "){" + func[3] + "}")
            for func in functions if len(func) == 4]  # 仅返回包含四个元素的元组



# 步骤 3: 将相同名字的函数对写入 Markdown 文件
def write_to_markdown(matching_files, files1, files2, project_dir1, project_dir2, output_file):
    total_files = len(matching_files)
    print(f"开始处理 {total_files} 对匹配文件，并将结果写入 Markdown 文件...")

    with open(output_file, 'w', encoding='utf-8') as md_file:
        for idx, (ts_rel_path, java_rel_path, filename) in enumerate(matching_files, 1):

            ts_filename = next(f for f in files1[filename] if f[1].endswith('.ts'))[1]
            java_filename = next(f for f in files2[filename] if f[1].endswith('.java'))[1]
            print(f"正在处理第 {idx}/{total_files} 对文件：{ts_filename} 和 {java_filename}")

            ts_functions = extract_functions_with_content(
                os.path.join(project_dir1, ts_rel_path, ts_filename), 'ts'
            )
            java_functions = extract_functions_with_content(
                os.path.join(project_dir2, java_rel_path, java_filename), 'java'
            )

            # 获取函数名相同的函数
            ts_function_names = {func[0]: func[1] for func in ts_functions}
            java_function_names = {func[0]: func[1] for func in java_functions}
            common_functions = set(ts_function_names.keys()).intersection(java_function_names.keys())

            if common_functions:
                ts_rel_path_full = os.path.join(ts_rel_path, ts_filename)
                java_rel_path_full = os.path.join(java_rel_path, java_filename)

                md_file.write(f"### {ts_rel_path_full} 和 {java_rel_path_full} 中相同的函数\n")
                for func in common_functions:
                    md_file.write(f"- 函数名: {func}\n")
                    md_file.write(f"- TS 函数内容:\n```typescript\n{ts_function_names[func]}\n```\n")
                    md_file.write(f"- Java 函数内容:\n```java\n{java_function_names[func]}\n```\n")
                md_file.write("\n")

            # 打印单个文件对处理完成
            print(f"完成处理文件对 {idx}/{total_files}。")

    print(f"所有文件处理完成，结果已写入：{output_file}")


# 主函数：运行代码
def main(project_dir1, project_dir2, output_file):
    print("开始扫描和处理项目文件...")
    matching_files, files1, files2 = find_matching_files(project_dir1, project_dir2)

    if matching_files:
        print("匹配的文件找到，开始提取函数并写入结果...")
        write_to_markdown(matching_files, files1, files2, project_dir1, project_dir2, output_file)
        print(f"任务完成！Markdown 文件已生成：{output_file}")
    else:
        print("没有找到匹配的文件。")


# 调用主函数
if __name__ == "__main__":
    project_dir2 = ""
    project_dir1 = ""
    output_file = "./output.md"

    main(project_dir1, project_dir2, output_file)
