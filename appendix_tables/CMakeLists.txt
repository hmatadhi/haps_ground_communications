cmake_minimum_required(VERSION 3.16)
project(HAPS_Figure_Generation LANGUAGES NONE)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(OUTPUT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/output")
file(MAKE_DIRECTORY "${OUTPUT_DIR}")

add_custom_target(generate_outputs ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Running Python generators..."
    COMMAND ${CMAKE_COMMAND} -E chdir "${CMAKE_CURRENT_SOURCE_DIR}"
            ${Python3_EXECUTABLE} -c "import glob, os, shutil, subprocess, sys; root = os.getcwd(); gen = os.path.join(root, 'generators'); out = os.path.join(root, 'output'); os.makedirs(out, exist_ok=True); files = sorted(glob.glob(os.path.join(gen, '*.py'))); print(f'Running {len(files)} generator(s)');
for f in files:
    subprocess.run([sys.executable, f], check=True, cwd=root)
patterns = ('*.png', '*.pdf', '*.csv', '*.tex', '*.txt')
seen = set()
for pat in patterns:
    for p in glob.glob(os.path.join(root, '**', pat), recursive=True):
        if not os.path.isfile(p):
            continue
        rel = os.path.relpath(p, root)
        if 'output' in rel.split(os.sep):
            continue
        seen.add(rel)
for rel in sorted(seen):
    src = os.path.join(root, rel)
    dst = os.path.join(out, os.path.basename(rel))
    shutil.copy2(src, dst)
    print(f'copied {rel} -> {os.path.basename(rel)}')"
    COMMENT "Run all Python generators and copy generated artifacts into output/"
    VERBATIM
)

add_custom_target(run_generators
    COMMAND ${CMAKE_COMMAND} -E echo "Running all Python generators"
    COMMAND ${CMAKE_COMMAND} -E chdir "${CMAKE_CURRENT_SOURCE_DIR}"
            ${Python3_EXECUTABLE} -c "import glob, subprocess, sys; root = '.'; files = sorted(glob.glob('generators/*.py')); [subprocess.run([sys.executable, f], check=True, cwd=root) for f in files]"
    COMMENT "Execute every figure/table generator under src/generators"
    VERBATIM
)

add_custom_target(clean_outputs
    COMMAND ${CMAKE_COMMAND} -E rm -rf "${OUTPUT_DIR}"
    COMMENT "Remove generated output files"
    VERBATIM
)

# PowerShell usage:
#   cd C:\Github\haps_ground_communications\src
#   cmake -S . -B build
#   cmake --build build
#   cmake --build build --target clean_outputs
