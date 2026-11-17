from compute_forecast.market_analysis_v19 import paired
def test_weighted_pairs_and_origin_unit():
    cells=[]
    for origin,values in (("a",[1,3]),("b",[-2])):
        for i,value in enumerate(values):
            for method,loss in (("candidate",10+value),("reference",10)):
                cells.append({"origin":origin,"series_id":str(i),"horizon_days":7,"method":method,"loss":loss})
    result=paired(cells,"candidate","reference",replicates=30)
    assert result["estimate"]==2/3 and result["cells"]==3 and result["n_origins"]==2
    assert result["block_sensitivity"]["4"] is None
    assert result==paired(cells,"candidate","reference",replicates=30)
