"""Render-only exclusions occupied by authored physical stair treads/landings.
Does not alter OSM paths, road widths, routing edges or source feature identity.
"""
def detailed_stair_exclusion():
 from shapely.geometry import box
 from shapely.ops import unary_union
 return unary_union([box(-5.6,-92,5.6,-81.9),box(-3.9,-81.9,3.9,-27),box(-5.9,-96,5.9,-92),box(-4.55,-27,4.55,-24.4)])
