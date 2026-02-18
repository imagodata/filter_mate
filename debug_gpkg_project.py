"""Diagnostic script: extract and inspect project XML from a GPKG.

Usage in QGIS Python console:
    exec(open('C:/Users/SimonDucorneau/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/filter_mate/debug_gpkg_project.py').read())

Then call:
    inspect_gpkg(r"C:\path\to\your\exported.gpkg")
"""
import sqlite3
import zipfile
import io


def inspect_gpkg(gpkg_path):
    """Extract and print project XML + SRS info from a GPKG."""
    conn = sqlite3.connect(gpkg_path)
    cur = conn.cursor()

    # 1. Check gpkg_spatial_ref_sys
    print("=" * 60)
    print("gpkg_spatial_ref_sys:")
    print("=" * 60)
    try:
        cur.execute("SELECT srs_id, organization, organization_coordsys_id, srs_name FROM gpkg_spatial_ref_sys")
        for row in cur.fetchall():
            print(f"  srs_id={row[0]}, org={row[1]}, code={row[2]}, name={row[3]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # 2. Check gpkg_geometry_columns
    print("\n" + "=" * 60)
    print("gpkg_geometry_columns:")
    print("=" * 60)
    try:
        cur.execute("SELECT table_name, column_name, geometry_type_name, srs_id FROM gpkg_geometry_columns")
        for row in cur.fetchall():
            print(f"  table={row[0]}, geom_col={row[1]}, type={row[2]}, srs_id={row[3]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # 3. Check qgis_projects
    print("\n" + "=" * 60)
    print("qgis_projects:")
    print("=" * 60)
    try:
        cur.execute("SELECT name, length(content) FROM qgis_projects")
        rows = cur.fetchall()
        if not rows:
            print("  (empty - no project embedded!)")
        for row in rows:
            print(f"  name='{row[0]}', content_length={row[1]}")
    except sqlite3.OperationalError:
        print("  (table does not exist - no project embedded!)")

    # 4. Extract and show project XML
    print("\n" + "=" * 60)
    print("Project XML (CRS-related elements):")
    print("=" * 60)
    try:
        cur.execute("SELECT name, content FROM qgis_projects LIMIT 1")
        row = cur.fetchone()
        if row:
            name, hex_content = row
            # Decode hex → bytes → unzip QGZ → XML
            try:
                qgz_bytes = bytes.fromhex(hex_content)
                zf = zipfile.ZipFile(io.BytesIO(qgz_bytes))
                for fname in zf.namelist():
                    print(f"\n  QGZ contains: {fname}")
                    xml_str = zf.read(fname).decode('utf-8')

                    # Show projectCrs
                    import re
                    # Find projectCrs
                    m = re.search(r'<projectCrs>.*?</projectCrs>', xml_str, re.DOTALL)
                    if m:
                        print(f"\n  <projectCrs>:")
                        print(f"    {m.group()[:500]}")
                    else:
                        print("\n  <projectCrs>: NOT FOUND!")

                    # Find mapcanvas destinationsrs
                    m = re.search(r'<mapcanvas.*?</mapcanvas>', xml_str, re.DOTALL)
                    if m:
                        print(f"\n  <mapcanvas>:")
                        print(f"    {m.group()[:500]}")
                    else:
                        print("\n  <mapcanvas>: NOT FOUND!")

                    # Find first maplayer srs
                    m = re.search(r'<maplayer.*?<srs>(.*?)</srs>', xml_str, re.DOTALL)
                    if m:
                        print(f"\n  First <maplayer><srs>:")
                        print(f"    {m.group(1)[:500]}")

                    # Save full XML for inspection
                    out_path = gpkg_path.replace('.gpkg', '_project.qgs')
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(xml_str)
                    print(f"\n  Full XML saved to: {out_path}")

            except Exception as e:
                print(f"  Error decoding project: {e}")
                # Try raw (non-hex, non-zip)
                print(f"  Raw content preview: {hex_content[:200]}")
        else:
            print("  No project found")
    except Exception as e:
        print(f"  ERROR: {e}")

    conn.close()
    print("\n" + "=" * 60)
    print("Done.")
