"""Conditional family exclusions, separate from protected acceptance."""
def add_closed_overlap_cuts(model,xs,fixed,cuts,baseline=225):
 total=sum(xs.values())+len(fixed);large=model.new_bool_var("strictly_larger_than_seed")
 model.add(total>=baseline+1).only_enforce_if(large);model.add(total<=baseline).only_enforce_if(large.Not())
 rows=[]
 for i,row in enumerate(cuts):
  S=set(row["words"]);available=[xs[w] for w in S-fixed if w in xs];constant=len(fixed&S)
  model.add(sum(available)+constant<=row["limit"]).only_enforce_if(large)
  rows.append({"cut":i,"fixed_overlap":constant,"eligible_variable_words":len(available),"limit":row["limit"]})
 return rows
