option(V2_STUDIO_ENABLE_QT "Build the Qt-based v2 studio application" ON)

set(V2_STUDIO_SOURCES app/main_stub.cpp)
set(V2_STUDIO_LINK_LIBS "")

if(V2_STUDIO_ENABLE_QT)
    find_package(Qt6 COMPONENTS Widgets Gui Core QUIET)
    if(Qt6Widgets_FOUND AND Qt6Gui_FOUND AND Qt6Core_FOUND)
        set(V2_STUDIO_SOURCES app/main.cpp)
        list(APPEND V2_STUDIO_LINK_LIBS Qt6::Widgets Qt6::Gui Qt6::Core v2_engine)
        set(CMAKE_AUTOMOC ON)
        set(CMAKE_AUTORCC ON)
        set(CMAKE_AUTOUIC ON)
    else()
        message(WARNING "Qt6 not found; building placeholder v2_studio without Qt.")
    endif()
endif()

add_executable(v2_studio ${V2_STUDIO_SOURCES})

target_compile_features(v2_studio PRIVATE cxx_std_20)

if(V2_STUDIO_LINK_LIBS)
    target_link_libraries(v2_studio PRIVATE ${V2_STUDIO_LINK_LIBS})
endif()
