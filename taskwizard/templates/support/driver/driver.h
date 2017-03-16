{% import "macro.cpp.j2" as macro %}

#include "support_proto.h"

{% for interface in task.interfaces.values() %}
    {{ macro.generate_protocol_header(
        interface.functions.values(),
        interface.callback_functions.values(),
        driver=True,
        interface_name=interface.name) }}
{% endfor %}

{{ macro.generate_protocol_header([], driver.functions.values()) }}
