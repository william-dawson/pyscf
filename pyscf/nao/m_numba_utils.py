from __future__ import division
import numpy as np
import numba as nb
from pyscf.nao.m_fact import sgn, onedivsqrt4pi

"""
    numba functions to performs some basics operations
"""

@nb.jit(nopython=True)
def ls_contributing_numba(atom2coord, ia2dist):

    for ia in range(atom2coord.shape[0]):
        rvec = atom2coord[ia, :]
        ia2dist[ia] = np.sqrt(np.dot(rvec, rvec))

@nb.jit(nopython=True)
def triu_indices_numba(ind, dim):

    count = 0
    for i in range(dim):
        for j in range(i, dim):
            ind[i, j] = count
            count += 1

@nb.jit(nopython=True)
def fill_triu(mat, ind, triu, s1, f1, s2, f2, add = False):
    
    if add:
        for i1 in range(s1,f1):
            for i2 in range(s2,f2):
                if ind[i1, i2] >= 0:
                    triu[ind[i1, i2]] += mat[i1-s1,i2-s2]
    else:
        for i1 in range(s1,f1):
            for i2 in range(s2,f2):
                if ind[i1, i2] >= 0:
                    triu[ind[i1, i2]] = mat[i1-s1,i2-s2]
 
@nb.jit(nopython=True)
def fill_triu_v2(block, triu, s1, f1, s2, f2, N, add = False):
    """
    Fill upper triangular matrice block by block.
    Input:
    ------
        block: a block of the full matrix
        s1, s2: start indices of the block (row/col)
        f1, f2: end indices of the block (row/col)
        N: number of row (col) of the matrix, the matrix must be square => dim = NxN
        add (optional): boollean, to add value to a already existing matrix
    Output:
    -------
       triu: upper part of the square matrix, dim = Nx(N-1)//2
    """

    if add:
        for i1 in range(s1,f1):
            for i2 in range(s2,min(i1+1, f2)):
                ind = 0
                if i2 > 0:
                    for beta in range(1, i2+1):
                        ind += N -beta
                ind += i1
                triu[ind] += block[i1-s1,i2-s2]
    else:
        for i1 in range(s1,f1):
            for i2 in range(s2, min(i1+1, f2)):
                ind = 0
                if i2 > 0:
                    for beta in range(1, i2+1):
                        ind += N -beta
                ind += i1
                triu[ind] = block[i1-s1,i2-s2]

@nb.jit(nopython=True)
def fill_tril(block, tril, s1, f1, s2, f2, ind, add = False):
    """
    Fill lower triangular matrice block by block.
    Input:
    ------
        block: a block of the full matrix
        s1, s2: start indices of the block (row/col)
        f1, f2: end indices of the block (row/col)
        N: number of row (col) of the matrix, the matrix must be square => dim = NxN
        add (optional): boollean, to add value to a already existing matrix
    Output:
    -------
       triu: upper part of the square matrix, dim = Nx(N-1)//2
    """

    if add:
        for i1 in range(s1,f1):
            for i2 in range(s2, min(i1+1, f2)):
                tril[ind] += block[i1-s1,i2-s2]
                ind += 1
    else:
        for i1 in range(s1,f1):
            for i2 in range(s2, min(i1+1, f2)):
                tril[ind] = block[i1-s1,i2-s2]
                ind += 1


#
#
#
@nb.jit(nopython=True)
def csphar_numba(r,lmax):
  """
    Computes (all) complex spherical harmonics up to the angular momentum lmax
    
    Args:
      r : Cartesian coordinates defining correct theta and phi angles for spherical harmonic
      lmax : Integer, maximal angular momentum
    Result:
      1-d numpy array of complex128 elements with all spherical harmonics stored in order 0,0; 1,-1; 1,0; 1,+1 ... lmax,lmax, althogether 0 : (lmax+1)**2 elements.
  """
  x=r[0]
  y=r[1] 
  z=r[2] 
  dd=np.sqrt(x*x+y*y+z*z)
  res = np.zeros(((lmax+1)**2), dtype=np.complex128)

  res[0] = onedivsqrt4pi

  if dd < 1.0e-10 :
     ll=(lmax+1)**2
     return res

  if x == 0.0 :
    phi=0.5*np.pi
    if y<0.0: phi=-phi
  else:
    phi = np.arctan( y/x ) 
    if x<0.0: phi=phi+np.pi 

  ss=np.sqrt(x*x+y*y)/dd
  cc=z/dd
  
  if lmax<1 : return res
  
  for l in range(1,lmax+1):
     al=1.0*l 
     il2=(l+1)**2-1 
     il1=l**2-1
     res[il2] = -ss*np.sqrt((al-0.5)/al)*res[il1] 
     res[il2-1] = cc*np.sqrt(2.0*al-1.0)*res[il1]

  if lmax>1:
    for m in range(lmax-1):
      if m<lmax:
        for l in range(m+1,lmax):
          ind=l*(l+1)+m 
          aa=1.0*(l**2-m**2)
          bb=1.0*((l+1)**2-m**2)
          zz=(l+l+1.0)*cc*res[ind].real-np.sqrt(aa)*res[ind-2*l].real 
          res[ind+2*(l+1)]=zz/np.sqrt(bb) 

  for l in range(lmax+1):
     ll2=l*(l+1)
     rt2lp1=np.sqrt(l+l+1.0)
     for m in range(l+1):
        cs=np.sin(m*phi)*rt2lp1
        cc=np.cos(m*phi)*rt2lp1
        res[ll2+m]=np.complex(cc,cs)*res[ll2+m]
        res[ll2-m]=sgn[m]*np.conj(res[ll2+m])
  
  return res


#
#
#
def comp_coeffs_numba(gammin_jt, dg_jt, nr, r, i2coeff):
    """
    Interpolation of a function given on the logarithmic mesh (see m_log_mesh how this is defined)
        6-point interpolation on the exponential mesh (James Talman)
    Args:
        r  : radial coordinate for which we want the intepolated value
    Result: 
    Array of weights to sum with the functions values to obtain the interpolated value coeff
    and the index k where summation starts sum(ff[k:k+6]*coeffs)
    """
    if r<=0.0:
        i2coeff[:] = 0.0
        i2coeff[0] = 1
        return 0

    lr = np.log(r)
    k  = int((lr-gammin_jt)/dg_jt)
    k  = min(max(k,2), nr-4)
    dy = (lr-gammin_jt-k*dg_jt)/dg_jt
    
    i2coeff[0] =     -dy*(dy**2-1.0)*(dy-2.0)*(dy-3.0)/120.0
    i2coeff[1] = +5.0*dy*(dy-1.0)*(dy**2-4.0)*(dy-3.0)/120.0
    i2coeff[2] = -10.0*(dy**2-1.0)*(dy**2-4.0)*(dy-3.0)/120.0
    i2coeff[3] = +10.0*dy*(dy+1.0)*(dy**2-4.0)*(dy-3.0)/120.0
    i2coeff[4] = -5.0*dy*(dy**2-1.0)*(dy+2.0)*(dy-3.0)/120.0
    i2coeff[5] =      dy*(dy**2-1.0)*(dy**2-4.0)/120.0
    
    return k-2
