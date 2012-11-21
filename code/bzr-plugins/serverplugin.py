from bzrlib import branch
import traceback
try:
    from branchinfo import BranchInfoCache
except:
    import sys
    sys.path.append('/data/buildscripts')
    from branchinfo import BranchInfoCache

version_info = (0,0,2, 'dev')

reporootname = 'reporoot'

def get_branch_parts_from_base(base):
    branchname = ''
    componentname = ''
    aspectname = ''
    branchparts = base.split('/')
    if reporootname in branchparts:
        start = branchparts.index(reporootname)
        if len(branchparts) >= start + 4:
            branchname, componentname, aspectname = branchparts[start+1: start+4]
        else: # if not this isn't a component aspect
            pass
    else: # not working in the managed repository
        pass
    return branchname, componentname, aspectname


def update_branch_info(base, revid):
    branchname,componentname,aspectname = get_branch_parts_from_base(base)
    if branchname:
        cache = BranchInfoCache('/reporoot')
        cache.update(branchname, componentname, aspectname, revid)

    
def post_change_branch_hook(changebranchparams):
    update_branch_info(changebranchparams.branch.base, changebranchparams.new_revid)
            

def post_branch_init_hook(params):
    update_branch_info(params.branch.base, params.branch.last_revision())

def post_branch_pull_hook(params):
    update_branch_info(params.branch.base, params.new_revid)

try:
    branch.Branch.hooks.install_named_hook('post_branch_init', post_branch_init_hook, 'post branch init hook')
    branch.Branch.hooks.install_named_hook('post_change_branch_tip', post_change_branch_hook, 'post change hook')
    branch.Branch.hooks.install_named_hook('post_branch_pull_hook', post_branch_pull_hook, 'post pull hook')
except:
    pass
   #traceback.print_exc()

