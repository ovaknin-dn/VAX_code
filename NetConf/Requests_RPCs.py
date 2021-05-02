REQUEST_TECH_SUPPORT = """<rpc message-id="101" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><request-tech-support></request-tech-support></rpc>"""


SHOW_SYSTEM = """
<rpc message-id="101" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
    <show-system xmlns="http://drivenets.com/ns/yang/dn-rpc">
        <result />
    </show-system>
</rpc>
"""

AA = """
     <rpc message-id="101" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
<show-route-summary></show-route-summary>
     </rpc>
"""
