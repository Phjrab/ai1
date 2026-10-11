"""Validate a bounded repair as a second, explicit authoring phase."""
import hashlib,json

def verify_repair_provenance(manifest,root):
    expected=manifest.get('bounded_repair_plan_sha256')
    if not expected:return None
    relative='realism_v2/final_repairs/patch_plan.json';raw=(root/relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected,'Bounded repair plan changed after native export'
    plan=json.loads(raw)
    assert plan['schema']=='chosun.bounded-final-repair-plan.v1' and plan['ready_for_bounded_build'] and not plan.get('pending'),'Unfrozen repair plan'
    assert plan['base_native_sha256']==manifest['bounded_repair_base_native_sha256'],'Repair base native differs'
    assert plan['historical_integration_plan_sha256']==manifest['integration_plan_sha256'],'Historical authoring phase changed'
    for path,change in plan.get('source_overrides',{}).items():
        assert plan['base_module_hashes'].get(path)==change['before_sha256'],'Override does not match its historical source'
        assert manifest['module_sha256'].get(path)==change['after_sha256'],'Override does not match the final native source'
    return {'plan':relative,'sha256':expected,'baseNativeSha256':plan['base_native_sha256'],'historicalIntegrationPlanSha256':plan['historical_integration_plan_sha256'],'sourceOverrides':plan.get('source_overrides',{})}
