import math
import pytest
from sports_vision.analytics import PlayerAccumulator
@pytest.mark.parametrize('time,position',[(float('nan'),(1.,0.)),(2.,(float('inf'),0.)),(2.,(float('nan'),0.))])
def test_nonfinite_samples_do_not_poison_next_measurement(time,position):
 p=PlayerAccumulator(1);p.update(0.,(0.,0.));p.update(time,position);p.update(1.,(1.,0.))
 assert p.distance_m==pytest.approx(1.)
 assert p.last_time_s==1.
 assert p.samples==2

def test_out_of_order_sample_does_not_rewind_tracking_state():
 p=PlayerAccumulator(1);p.update(0.,(0.,0.));p.update(1.,(1.,0.));p.update(.5,(20.,0.));p.update(2.,(2.,0.))
 assert p.distance_m==pytest.approx(2.)
 assert p.samples==3
