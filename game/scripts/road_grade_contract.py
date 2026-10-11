"""Validate densified original roads and explicitly authorized added connections."""
import math

def approved_landmark_relocations(contract,entrances):
    """Only the level-revision buildings' explicit named entrance arrivals."""
    ids={str(b['id']) for b in contract['buildings']};approved={}
    for record in entrances['records']:
        key=str(record['building_id'])
        if key not in ids or not record.get('is_landmark_destination') or record.get('student_union_level_version')!=contract['version']:continue
        point=record['safe_arrival']
        assert len(point)==3 and all(math.isfinite(v) for v in point)
        assert key not in approved,'Duplicate level-revised named entrance'
        approved[key]={'position':point,'entrance_id':record['entrance_id']}
    return approved

def runtime_roads(vehicle):
    """Retain native route identity/direction while converting spatial points."""
    records=[]
    for edge in vehicle['edges']:
        record={'name':'CAMPUS_ROAD '+str(edge.get('osm_id','')),
                'width':edge['width'],
                'points':[[p[0],p[2],-p[1]] for p in (vehicle['nodes'][edge['a']],vehicle['nodes'][edge['b']])]}
        for key in ['connection_id','osm_id','highway','oneway','access','source','support_surface_objects']:
            if key in edge:record[key]=edge[key]
        records.append(record)
    return records

def previous_road_heights(old_graph,vehicle,added_connections,corrected_nodes=()):
    original_by_osm={}
    for edge in old_graph['edges']:original_by_osm.setdefault(str(edge.get('osm_id','')),[]).append(edge)
    connections={record['id']:record for record in added_connections}
    assert len(connections)==len(added_connections),'Duplicate added connection ID'
    incident={};incident_indices={};accepted_nodes=set()
    for edge_index,edge in enumerate(vehicle['edges']):
        for index in [edge['a'],edge['b']]:incident.setdefault(index,[]).append(edge)
        for index in [edge['a'],edge['b']]:incident_indices.setdefault(index,set()).add(edge_index)
        key=edge.get('connection_id')
        if key is None:continue
        assert key in connections,'Unbound added road connection: '+str(key)
        contract=connections[key]
        assert str(edge['osm_id'])==str(contract['osm_id']),'Added road OSM identity mismatch'
        assert contract.get('source') and contract['width_m']>0,'Added road provenance/width required'
        assert abs(edge['width']-contract['width_m'])<1e-6,'Added road width differs from approved contract'
        assert all(i in contract['node_indices'] for i in [edge['a'],edge['b']]),'Added road uses undeclared node'
        accepted_nodes.update([edge['a'],edge['b']])
    for contract in added_connections:
        actual={i for e in vehicle['edges'] if e.get('connection_id')==contract['id'] for i in [e['a'],e['b']]}
        assert actual==set(contract['node_indices']),'Added connection node set differs from native contract'
    corrections={}
    for record in corrected_nodes:
        index=record['node_index']
        assert isinstance(index,int) and not isinstance(index,bool) and 0<=index<len(vehicle['nodes']),'Invalid corrected road node index'
        assert index not in corrections,'Duplicate corrected road node'
        original,new=record['original_position'],record['new_position']
        assert all(len(p)==3 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in [original,new]),'Corrected road positions must be finite XYZ'
        assert isinstance(record.get('source'),str) and record['source'].strip(),'Corrected road provenance required'
        edges=record['affected_edges']
        assert isinstance(edges,list) and edges and all(isinstance(i,int) and not isinstance(i,bool) for i in edges),'Corrected road requires explicit final edge indices'
        assert len(edges)==len(set(edges)) and set(edges)==incident_indices.get(index,set()),'Corrected road incident edges differ from contract'
        assert math.dist(new,vehicle['nodes'][index])<=1e-5,'Corrected road final XYZ differs from contract'
        assert math.dist(original[:2],new[:2])>1e-6,'Corrected road contract has no XY change'
        if index<len(old_graph['nodes']):
            assert math.dist(original[:2],old_graph['nodes'][index][:2])<=1e-6,'Corrected road original XY differs from baseline node'
        corrections[index]=original
    result=[]
    for index,point in enumerate(vehicle['nodes']):
        if index>=len(old_graph['nodes']) and index not in incident:
            result.append(None);continue # Retained unused densification nodes do not define a road.
        source_point=corrections.get(index,point)
        if index<len(old_graph['nodes']) and math.dist(source_point[:2],old_graph['nodes'][index][:2])<1e-6:
            result.append(old_graph['nodes'][index][2]);continue
        if index<len(old_graph['nodes']):raise ValueError('Original road node XY changed without an exact native correction: '+str(index))
        candidates=[]
        for osm in {str(e.get('osm_id','')) for e in incident.get(index,[])}:
            for edge in original_by_osm.get(osm,[]):
                a,b=[old_graph['nodes'][edge[k]] for k in ['a','b']];dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((source_point[0]-a[0])*dx+(source_point[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
                candidates.append((math.hypot(source_point[0]-a[0]-t*dx,source_point[1]-a[1]-t*dy),a[2]+t*(b[2]-a[2])))
        if candidates and min(candidates)[0]<=.01:result.append(min(candidates)[1]);continue
        if index in corrections:raise ValueError('Corrected road original XY leaves its mapped source route: '+str(index))
        if index>=len(old_graph['nodes']) and index in accepted_nodes and all(e.get('connection_id') in connections for e in incident[index]):result.append(None);continue
        raise ValueError('Revised road node leaves its original mapped XY route: '+str(index))
    return result
