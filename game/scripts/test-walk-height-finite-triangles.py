import importlib.util,pathlib,unittest,math
ROOT=pathlib.Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('height',ROOT/'realism_v2/walk_route_alignment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FiniteTriangles(unittest.TestCase):
 def test_actual_550_sliver_does_not_support_its_distant_extension(self):
  vertices=[[250.,-350.,-40.0850715637207],[249.38963317871094,-350.6103515625,-40.0850715637207],[249.3896484375,-350.6103515625,-40.0850715637207],[254.,-346.,-41.158573150634766],[256.,-346.,-41.158573150634766],[255.,-344.,-41.158573150634766]];q=m.triangle_height_index(vertices,[(0,1,2),(3,4,5)]);self.assertEqual(q((255.,-345.))[0],-41.158573150634766);self.assertEqual(q((250.,-350.))[0],-40.0850715637207)
 def test_true_floor_interior_and_float32_boundary_tolerance(self):
  q=m.triangle_height_index([(0.,0.,1.),(2.,0.,2.),(0.,2.,1.)],[(0,1,2)])
  self.assertAlmostEqual(q((.5,.5))[0],1.25);self.assertIsNotNone(q((1.,-0.00008)));self.assertIsNone(q((1.,-.0002)));self.assertIsNone(q((2.00008,-.00008)))
 def test_face_order_and_winding_do_not_change_height(self):
  vertices=[(0.,0.,1.),(2.,0.,2.),(0.,2.,1.)];a=m.triangle_height_index(vertices,[(0,1,2)]);b=m.triangle_height_index(vertices,[(0,2,1)])
  for p in [(0,0),(.5,.5),(1,.99998),(-.00005,1)]:self.assertAlmostEqual(a(p)[0],b(p)[0])
if __name__=='__main__':unittest.main()
