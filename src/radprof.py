import cProfile
from pstats import Stats

import OpenRadar

with cProfile.Profile() as pr:

    OpenRadar.main()

    stats = Stats(pr)
    stats.sort_stats('tottime').print_stats(20)
    pr.disable()
