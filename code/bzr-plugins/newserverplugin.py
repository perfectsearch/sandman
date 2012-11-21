from bzrlib import branch
import traceback
from reposupport import supportdir, reporootname, update_branch_info

version_info = (0,0,2, 'dev')


def get_branchpath_from_base(base):
    branchpath = None
    branchparts = base.split('/')
    if reporootname in branchparts:
        start = branchparts.index(reporootname)
        if len(branchparts) >= start + 4:
            branchpath = '/'.join(branchparts[start+1: start+4])
        else: # if not this isn't a component aspect
            pass
    else: # not working in the managed repository
        pass
    return branchpath


def update_branch_info(base, new_revno):
    branchpath = get_branchpath_from_base(base)
    if branchpath:
        update_branch_info(branchpath, new_revno)

    
def post_change_branch_hook(changebranchparams):
    update_branch_info(changebranchparams.branch.base, changebranchparams.new_revno)
            

def post_branch_init_hook(params):
    update_branch_info(params.branch.base, "0")


try:
    branch.Branch.hooks.install_named_hook('post_branch_init', post_branch_init_hook, 'post branch init hook')
    branch.Branch.hooks.install_named_hook('post_change_branch_tip', post_change_branch_hook, 'post change hook')
except:
    pass
    #traceback.print_exc()
