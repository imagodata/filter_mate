# -*- coding: utf-8 -*-
"""The agent's sources against the real services: needs the network, reads public data, sends nothing else.

    docker run --rm -v "$PWD:/src:ro" -e FM_REPO=/tmp/copy qgis/qgis:ltr bash -c \\
        'mkdir /tmp/copy; cp -r /src/. /tmp/copy; python3 /tmp/copy/tests/qgis_headless/check_agent_sources_live.py'
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import Qgis, QgsApplication, QgsProject  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:300]}" if not condition else ""), flush=True)


def main():
    from filter_mate.adapters.agent.mcp_connection import McpConnection
    from filter_mate.adapters.public_api import project_control, wfs_catalog
    from filter_mate.core.agent.sources import BUILT_IN

    by_id = {source.id: source for source in BUILT_IN}
    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    for identifier in ("datagouv_mcp", "statsmcp", "ckan_mcp", "osm_mcp", "socrata_mcp", "publicdata_au"):
        try:
            tools = McpConnection(by_id[identifier]).list_tools()
            check(f"{identifier}: lists tools", len(tools) > 0, tools)
        except Exception as exc:
            check(f"{identifier}: lists tools", False, exc)
    connection = McpConnection(by_id["datagouv_mcp"])
    remote = {tool.remote_name for tool in connection.list_tools()}
    check("data.gouv: search_datasets exists", "search_datasets" in remote, remote)
    answer = connection.call_tool("search_datasets", {"query": "communes", "page_size": 1})
    check("data.gouv: answers a search", "dataset" in answer.lower(), answer)

    for platform in ("datagouv", "opendatasoft", "data_gov_uk", "open_canada"):
        found = project_control.search_open_data("communes" if platform in ("datagouv", "opendatasoft") else "road", platform=platform, limit=3)
        check(f"{platform}: search", found["count"] > 0, found)

    found = project_control.search_open_data("commune admin express", platform="ign_wfs", limit=5)
    check("IGN: finds communes", found["count"] > 0 and ":commune" in " ".join(d["id"].lower() for d in found["datasets"]), found)
    typename = next(d["id"] for d in found["datasets"] if d["id"].lower().endswith(":commune"))
    summary = project_control.add_service_layer("ign_wfs", typename, name="communes_ign")
    check("IGN: a WFS layer opens", summary["provider_type"] == "WFS" and summary["name"] == "communes_ign", summary)
    try:
        project_control.add_service_layer("ign_wfs", "invented:layer' url='https://evil.example.org/wfs")
        check("IGN: a layer it does not list is refused", False)
    except ValueError:
        check("IGN: a layer it does not list is refused", True)

    for platform, query in (("ibge_br", "municipio"), ("prg_pl", "gmina")):
        listed = project_control.search_open_data(query, platform=platform, limit=3)
        check(f"{platform}: its capabilities are accepted", isinstance(listed.get("datasets"), list), listed)

    scenes = project_control.search_imagery(bbox=[1.3, 43.5, 1.5, 43.7], start="2026-06-01", end="2026-10-31", max_cloud=20, limit=2)
    check("Earth Search: scenes", scenes["count"] > 0 and scenes["datasets"][0]["resources"], scenes)
    visual = next(r for r in scenes["datasets"][0]["resources"] if r["format"] == "visual")
    image = project_control.add_layer(visual["url"], name="sentinel", kind="raster")
    layer = QgsProject.instance().mapLayersByName("sentinel")
    check("Earth Search: the image opens without downloading it", image["layer_kind"] == "raster" and layer and layer[0].bandCount() >= 3, image)


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(root, "filter_mate"))
    sys.path.insert(0, root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    print(f"{RESULTS.count(True)}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if RESULTS.count(False) else 0)
