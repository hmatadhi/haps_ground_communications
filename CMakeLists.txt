cmake_minimum_required(VERSION 3.16)
project(HAPS_AI_HW_ChannelModel LANGUAGES NONE)

# CMake is reserved for Python-generated tables and figures.
# The LaTeX paper itself is built via build-paper.bat.

find_package(Python3 COMPONENTS Interpreter QUIET)

set(GENERATE_TABLES_SCRIPT "${CMAKE_SOURCE_DIR}/scripts/generate_tables.py")
set(GENERATE_FIGURES_SCRIPT "${CMAKE_SOURCE_DIR}/scripts/generate_figures.py")

if(Python3_FOUND)
  if(EXISTS "${GENERATE_TABLES_SCRIPT}" OR EXISTS "${GENERATE_FIGURES_SCRIPT}")
    add_custom_target(generate_figures_and_tables
      COMMAND ${CMAKE_COMMAND} -E echo "Generating tables and figures from Python scripts..."
      COMMAND ${Python3_EXECUTABLE} ${GENERATE_TABLES_SCRIPT}
      COMMAND ${Python3_EXECUTABLE} ${GENERATE_FIGURES_SCRIPT}
      WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
      COMMENT "Running Python figure/table generation"
      VERBATIM
    )
  else()
    add_custom_target(generate_figures_and_tables
      COMMAND ${CMAKE_COMMAND} -E echo "No Python generator scripts found yet. Add scripts/generate_tables.py and/or scripts/generate_figures.py."
      WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
      COMMENT "No generators configured yet"
      VERBATIM
    )
  endif()
else()
  add_custom_target(generate_figures_and_tables
    COMMAND ${CMAKE_COMMAND} -E echo "Python3 not found. Install Python to enable table/figure generation."
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Python generation disabled"
    VERBATIM
  )
endif()

# Convenience target for future figure/table regeneration.
add_custom_target(generate
  DEPENDS generate_figures_and_tables
  COMMENT "Generate paper artifacts via Python"
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
