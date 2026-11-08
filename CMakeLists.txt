# SPDX-License-Identifier: GPL-2.0-only
cmake_minimum_required(VERSION 3.24)
project(jet_set_recomp LANGUAGES C CXX)

# A game repository is the top-level project and adds dream-recomp as a sibling of its game folder.
# The sub-project's own settings don't reach that sibling, so the language settings are repeated here.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/third_party/dream-recomp/CMakeLists.txt")
  message(FATAL_ERROR "third_party/dream-recomp is missing: run scripts/01_fetch_dream_recomp.sh")
endif()

add_subdirectory(third_party/dream-recomp)
add_subdirectory(games/jgr)
