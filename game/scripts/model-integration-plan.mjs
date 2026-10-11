// A module is active only when its source and every consumed sidecar were
// hash-bound to the exported native scene. A stale adjacent JSON is not input.
import path from 'node:path';
import {existsSync} from 'node:fs';
const features=[
 {id:'grade',module:'terrain_grounding.py',required:true,files:['verification/navigation_graded.json','verification/road_graph_3d_graded.json','verification/transit_placements_graded.json','verification/terrain_building_pads_graded.json','verification/ground_elevation_graded.json','verification/local_level_alignment.json']},
 {id:'actorGrounding',module:'terrain_level_reconciliation.py',modules:['actor_grounding_v5.py'],files:['terrain_v5/actor_grounding_v5.json']},
 {id:'roadSeams',module:'road_seam_metadata.py',files:['road_seam_repair_v5/game_cluster_routes.json']},
 {id:'studentLevels',module:'student_union_levels/student_union_levels.py',files:['student_union_levels/integration_contract.json']},
 {id:'garageRoadRepair',module:'final_garage_road_boundary.py',depends:['parking'],files:['final_garage_road_boundary/source_geometry.json','final_garage_road_boundary/applied_contract.json','final_garage_road_boundary/exterior_navigation.json','final_garage_road_boundary/exterior_navigation_qa.json']},
 {id:'parking',module:'parking_interior.py',required:true,files:['verification/parking_gameplay.json']},
 {id:'roof',module:'it_roof.py',required:true,files:['it_roof_review/bridge_navigation.json']},
 {id:'lounge',module:'it_lounge.py',files:['it_lounge_review/lounge_navigation.json']},
 {id:'itApproach',module:'final_it_approach_alignment.py',depends:['roof','lounge'],files:['it_approach_alignment_review/navigation_overlay.json']},
 {id:'itLowerRetirement',module:'final_it_lower_paving_retirement.py',depends:['itApproach'],files:['it_approach_alignment_review/lower_paving_retirement.json']},
 {id:'walkAlignment',module:'walk_route_alignment.py',depends:['entrances'],files:['walk_route_alignment/navigation_overlay.json']},
 {id:'entrances',module:'entrance_grounding_connections.py',modules:['entrances_a.py','entrances_b.py'],files:['entrances_a_overlay.json','entrances_b_overlay.json','entrance_connections/navigation.json','entrance_connections/audit.json']},
 {id:'haeoreum',module:'haeoreum_connections.py',depends:['entrances'],files:['terrain_v5/haeoreum_stair_navigation.json']},
 {id:'public',module:'public_spaces.py',files:['public_spaces_review/public_spaces_navigation.json','public_spaces_review/INTEGRATION_CONTRACT.json']},
 {id:'track',module:'track_perimeter.py',depends:['public'],files:['track_perimeter_review/track_navigation.json']},
 {id:'finitePaving',module:'final_pedestrian_contacts.py',modules:['final_pedestrian_legacy_surfaces.py'],files:['final_pedestrian_contacts/legacy_navigation_overlay.json']},
 {id:'pedestrianResiduals',module:'final_pedestrian_residuals.py',depends:['finitePaving','walkAlignment'],files:['final_pedestrian_residuals/resolved_navigation_overlay.json','final_pedestrian_residuals/applied_contract.json']},
 {id:'roseEndpoint',module:'rose_endpoint_paving.py',depends:['publicWalkRepair'],files:['final_rose_endpoint_join/rose_endpoint_paving_runtime.json']},
 {id:'publicWalkRepair',module:'public_walk_clearance.py',depends:['public','track'],files:['public_walk_clearance_review/navigation.json','public_walk_clearance_review/INTEGRATION_CONTRACT.json']},
 {id:'pharmacy',module:'entrances_supplement.py',depends:['entrances'],files:['entrances_supplement/navigation.json']},
 {id:'hospital',module:'hospital_arrival.py',depends:['entrances'],files:['hospital_arrival_review/hospital_arrival_overlay.json']},
 {id:'schools',module:'affiliated_schools.py',depends:['gates'],files:['affiliated_schools/overlay.json','affiliated_schools/source_geometry.json']},
 {id:'schoolRoadRepair',module:'final_foundation_contacts.py',depends:['schools'],files:['final_foundation_contacts/school_road_overlay.json']},
 {id:'gates',module:'gates_access.py',depends:['schools'],files:['gates_access/overlay.json']},
 {id:'pond',module:'pond_fountain.py',files:['pond_fountain/overlay.json']},
 {id:'pondEntry',module:'pond_entry_steps/repair.py',depends:['pond'],files:['pond_entry_steps/overlay.json']},
 {id:'terraceDriveAlignment',sidecarOnly:'terrace_drive_alignment/navigation.json',depends:['terraces'],files:['terrace_drive_alignment/navigation.json','terrace_drive_alignment/validation.json']},
 {id:'terraces',module:'parking_terraces_v5.py',files:['parking_terraces_v5/contract.json']},
 {id:'staticVehicles',module:'static_vehicle_grounding_v5.py',files:['static_vehicle_v5/final_vehicle_poses.json']},
 {id:'stopWalkways',module:'hospital_stop_walkways.py',depends:['hospital','transit'],files:['hospital_stop_walkways/hospital_stop_walkways_overlay.json']},
 {id:'greenery',module:'greenery_infill.py',files:['greenery_infill/game_tree_sidecar.json']},
 {id:'goals',module:'football_goals.py',files:['football_goals_review/goal_navigation.json']},
 {id:'transit',module:'transit_alignment.py',files:['transit_alignment_overlay.json','transit_review/integration_issues.json']}
];
export function integrationPlan(manifest,revision,{exists=existsSync}={}){
 const modules=manifest.module_sha256||{},sidecars=manifest.sidecar_sha256||{},active={};
 for(const feature of features){
  const present=feature.sidecarOnly?Object.hasOwn(sidecars,'realism_v2/'+feature.sidecarOnly):Object.hasOwn(modules,'realism_v2/'+feature.module);
  if(feature.required&&!present)throw new Error('Native export omits required module: '+feature.module);
  active[feature.id]=present;
  if(!present)continue;
  for(const other of feature.modules||[])if(!Object.hasOwn(modules,'realism_v2/'+other))throw new Error(feature.id+' requires native module '+other);
  for(const file of feature.files){
   if(!Object.hasOwn(sidecars,'realism_v2/'+file))throw new Error('Native '+feature.module+' has no bound runtime sidecar: '+file);
   if(!exists(path.join(revision,file)))throw new Error('Bound runtime sidecar is absent: '+file);
  }
 }
 for(const feature of features)if(active[feature.id])for(const dependency of feature.depends||[])if(!active[dependency])throw new Error(feature.id+' requires '+dependency);
 return active;
}
export const integrationFeatures=features;
