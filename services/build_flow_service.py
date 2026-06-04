# services/build_flow_service.py

BUILD_FLOW = [
    "start",
    "platform",
    "node",
    "interface",
    "squelch",
    "repeater",
    "cw",
    "ident",
    "courtesy",
    "modules",
    "reflector",
    "echolink",
    "metar_airports",
    "metar_default",
    "timezone",
    "review",
    "done",
]


def get_previous_page(current_page):
    if current_page not in BUILD_FLOW:
        return None

    index = BUILD_FLOW.index(current_page)

    if index == 0:
        return None

    return BUILD_FLOW[index - 1]


def get_next_page(current_page):
    if current_page not in BUILD_FLOW:
        return None

    index = BUILD_FLOW.index(current_page)

    if index >= len(BUILD_FLOW) - 1:
        return None

    return BUILD_FLOW[index + 1]


def get_navigation(current_page):
    return {
        "previous_page": get_previous_page(current_page),
        "next_page": get_next_page(current_page),
    }