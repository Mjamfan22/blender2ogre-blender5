"""Keep fixture-dependent checks explicit in a clean checkout."""
import os

FIXTURE_CASES = {
    'original_robot_animations', 'original_ogrehead',
    'existing_rig_name_is_not_reused', 'animated_robot_deformation_roundtrip',
    'issue240_reporter_swaptest_geometry_roundtrip', 'issue142_reporter_animated_character_roundtrip',
    'reported_bakugan_body_imports_all_three_base_textures', 'full_bakugan_import_matches_previous_release',
}
SKIPPED = []

def skip_fixture_case(name):
    if name in FIXTURE_CASES and os.environ.get('OGRE_FULL_TESTS') != '1':
        SKIPPED.append(name)
        print('SKIP', name, '(optional non-redistributed fixture; use --full)')
        return True
    return False
