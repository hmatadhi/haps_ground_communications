cmake_minimum_required(VERSION 3.16)
project(HAPS_AI_HW_ChannelModel LANGUAGES NONE)

# CMake is reserved for Python-generated tables and figures.
# The LaTeX paper itself is built via build-paper.bat.

set(GENERATE_SCRIPT "${CMAKE_SOURCE_DIR}/src/generate_all_wsl.sh")

# WSL bash is the only supported method (requires quantum_env)
if(EXISTS "${GENERATE_SCRIPT}")
  add_custom_target(generate_figures_and_tables
    COMMAND bash ${GENERATE_SCRIPT}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/src
    COMMENT "Running figure/table generation via WSL bash (quantum_env required)"
    VERBATIM
  )
else()
  add_custom_target(generate_figures_and_tables
    COMMAND ${CMAKE_COMMAND} -E echo "src/generate_all_wsl.sh not found."
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generate script not found"
    VERBATIM
  )
endif()

# Convenience target for figure/table regeneration
add_custom_target(generate
  DEPENDS generate_figures_and_tables
  COMMENT "Generate paper artifacts via WSL bash with quantum_env"
)

# Keep the paper compile outside CMake using build-paper.bat.
# Typical usage:
#   .\build-paper.bat

# Optional cleanup for generated paper artefacts
add_custom_target(clean-paper
  COMMAND ${CMAKE_COMMAND} -E rm -f
    ${CMAKE_SOURCE_DIR}/HAPS_AI_HW_ChannelModel.aux
    ${CMAKE_SOURCE_DIR}/HAPS_AI_HW_ChannelModel.log
    ${CMAKE_SOURCE_DIR}/HAPS_AI_HW_ChannelModel.out
    ${CMAKE_SOURCE_DIR}/HAPS_AI_HW_ChannelModel.pdf
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  COMMENT "Removing generated LaTeX files"
  VERBATIM
)

# Note: If using CMake on Windows, configure with:
#   cmake .. -G "Unix Makefiles"
# or use the Python/Bash scripts directly instead
