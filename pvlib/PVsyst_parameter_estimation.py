from scipy import optimize
import statsmodels.api as sm
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict
from pvlib.est_single_diode_param import est_single_diode_param
from pvlib.update_io_known_n import update_io_known_n
from pvlib.update_rsh_fixed_pt import update_rsh_fixed_pt
from pvlib.calc_theta_phi_exact import calc_theta_phi_exact
from pvlib.pvsystem import singlediode
plt.ion()


def numdiff(x, f):
    """
    NUMDIFF computes first and second order derivative using possibly unequally
    spaced data.

    Syntax
    ------
    df, df2 = numdiff(x,f)

    Description
    -----------
    numdiff computes first and second order derivatives using a 5th order
    formula that accounts for possibly unequally spaced data. Because a 5th
    order centered difference formula is used, numdiff returns NaNs for the
    first 2 and last 2 points in the input vector for x.

    Parameters
    ----------
    x: a numpy array of values of x
    f: a numpy array of values of the function f for which derivatives are to
       be computed. Must be the same length as x.

    Returns
    -------
    df: a numpy array of len(x) containing the first derivative of f at each
        point x except at the first 2 and last 2 points
    df2: a numpy array of len(x) containing the second derivative of f at each
         point x except at the first 2 and last 2 points.

    References
    ----------
    [1] PVLib MATLAB
    [2] M. K. Bowen, R. Smith, "Derivative formulae and errors for
        non-uniformly spaced points", Proceedings of the Royal Society A, vol.
        461 pp 1975 - 1997, July 2005. DOI: 10.1098/rpsa.2004.1430
    """

    n = len(f)

    df = np.zeros(len(f))
    df2 = np.zeros(len(f))

    # first two points are special
    df[0:2] = float("Nan")
    df2[0:2] = float("Nan")

    # Last two points are special
    df[(n - 2):n] = float("Nan")
    df2[(n - 2):n] = float("Nan")

    # Rest of points. Take reference point to be the middle of each group of 5
    # points. Calculate displacements
    ff = np.vstack((f[0:(n - 4)], f[1:(n - 3)], f[2:(n - 2)], f[3:(n - 1)],
                    f[4:n])).T

    a = np.vstack((x[0:(n - 4)], x[1:(n - 3)], x[2:(n - 2)], x[3:(n - 1)],
                   x[4:n])).T - np.tile(x[2:(n - 2)], [5, 1]).T

    u = np.zeros(a.shape)
    l = np.zeros(a.shape)
    u2 = np.zeros(a.shape)

    u[:, 0] = a[:, 1] * a[:, 2] * a[:, 3] + a[:, 1] * a[:, 2] * a[:, 4] + \
        a[:, 1] * a[:, 3] * a[:, 4] + a[:, 2] * a[:, 3] * a[:, 4]
    u[:, 1] = a[:, 0] * a[:, 2] * a[:, 3] + a[:, 0] * a[:, 2] * a[:, 4] + \
        a[:, 0] * a[:, 3] * a[:, 4] + a[:, 2] * a[:, 3] * a[:, 4]
    u[:, 2] = a[:, 0] * a[:, 1] * a[:, 3] + a[:, 0] * a[:, 1] * a[:, 4] + \
        a[:, 0] * a[:, 3] * a[:, 4] + a[:, 1] * a[:, 3] * a[:, 4]
    u[:, 3] = a[:, 0] * a[:, 1] * a[:, 2] + a[:, 0] * a[:, 1] * a[:, 4] + \
        a[:, 0] * a[:, 2] * a[:, 4] + a[:, 1] * a[:, 2] * a[:, 4]
    u[:, 4] = a[:, 0] * a[:, 1] * a[:, 2] + a[:, 0] * a[:, 1] * a[:, 3] + \
        a[:, 0] * a[:, 2] * a[:, 3] + a[:, 1] * a[:, 2] * a[:, 3]

    l[:, 0] = (a[:, 0] - a[:, 1]) * (a[:, 0] - a[:, 2]) * \
        (a[:, 0] - a[:, 3]) * (a[:, 0] - a[:, 4])
    l[:, 1] = (a[:, 1] - a[:, 0]) * (a[:, 1] - a[:, 2]) * \
        (a[:, 1] - a[:, 3]) * (a[:, 1] - a[:, 4])
    l[:, 2] = (a[:, 2] - a[:, 0]) * (a[:, 2] - a[:, 1]) * \
        (a[:, 2] - a[:, 3]) * (a[:, 2] - a[:, 4])
    l[:, 3] = (a[:, 3] - a[:, 0]) * (a[:, 3] - a[:, 1]) * \
        (a[:, 3] - a[:, 2]) * (a[:, 3] - a[:, 4])
    l[:, 4] = (a[:, 4] - a[:, 0]) * (a[:, 4] - a[:, 1]) * \
        (a[:, 4] - a[:, 2]) * (a[:, 4] - a[:, 3])

    df[2:(n - 2)] = np.sum(-(u / l) * ff, axis=1)

    # second derivative
    u2[:, 0] = a[:, 1] * a[:, 2] + a[:, 1] * a[:, 3] + a[:, 1] * a[:, 4] + \
        a[:, 2] * a[:, 3] + a[:, 2] * a[:, 4] + a[:, 3] * a[:, 4]
    u2[:, 1] = a[:, 0] * a[:, 2] + a[:, 0] * a[:, 3] + a[:, 0] * a[:, 4] + \
        a[:, 2] * a[:, 3] + a[:, 2] * a[:, 4] + a[:, 3] * a[:, 4]
    u2[:, 2] = a[:, 0] * a[:, 1] + a[:, 0] * a[:, 3] + a[:, 0] * a[:, 4] + \
        a[:, 1] * a[:, 3] + a[:, 1] * a[:, 3] + a[:, 3] * a[:, 4]
    u2[:, 3] = a[:, 0] * a[:, 1] + a[:, 0] * a[:, 2] + a[:, 0] * a[:, 4] + \
        a[:, 1] * a[:, 2] + a[:, 1] * a[:, 4] + a[:, 2] * a[:, 4]
    u2[:, 4] = a[:, 0] * a[:, 1] + a[:, 0] * a[:, 2] + a[:, 0] * a[:, 3] + \
        a[:, 1] * a[:, 2] + a[:, 1] * a[:, 4] + a[:, 2] * a[:, 3]

    df2[2:(n - 2)] = 2. * np.sum(u2 * ff, axis=1)
    return df, df2


def rectify_iv_curve(ti, tv, voc, isc):
    """
    rectify_IV_curve ensures that Isc and Voc are included in a IV curve and
    removes duplicate voltage and current points.

    Syntax
    ------
    I, V = rectify_IV_curve(ti, tv, voc, isc)

    Description
    -----------
    rectify_IV_curve ensures that the IV curve data
        * increases in voltage
        * contain no negative current or voltage values
        * have the first data point as (0, Isc)
        * have the last data point as (Voc, 0)
        * contain no duplicate voltage values. Where voltage values are
          repeated, a single data point is substituted with current equal to
          the average of current at each repeated voltage.

    Parameters
    ----------
    ti: a numpy array of length N containing the current data
    tv: a numpy array of length N containing the voltage data
    voc: a int or float containing the open circuit voltage
    isc: a int or float containing the short circuit current

    Returns
    -------
    I, V: numpy arrays of equal length containing the current and voltage
          respectively
    """
    # Filter out negative voltage and current values
    data_filter = []
    for n, i in enumerate(ti):
        if i < 0:
            continue
        if tv[n] > voc:
            continue
        if tv[n] < 0:
            continue
        data_filter.append(n)

    current = np.array([isc])
    voltage = np.array([0.])

    for i in data_filter:
        current = np.append(current, ti[i])
        voltage = np.append(voltage, tv[i])

    # Add in Voc and Isc
    current = np.append(current, 0.)
    voltage = np.append(voltage, voc)

    # Remove duplicate Voltage and Current points
    u, index, inverse = np.unique(voltage, return_index=True,
                                  return_inverse=True)
    if len(u) != len(voltage):
        v = []
        for i in u:
            fil = []
            for n, j in enumerate(voltage):
                if i == j:
                    fil.append(n)
            t = current[fil]
            v.append(np.average(t))
        voltage = u
        current = np.array(v)
    return current, voltage


def estrsh(x, rshexp, g, go):
    # computes rsh for PVsyst model where the parameters are in vector xL
    # x[0] = Rsh0
    # x[1] = Rshref

    rsho = x[0]
    rshref = x[1]

    rshb = np.max((rshref - rsho * np.exp(-rshexp)) / (1. - np.exp(-rshexp)),
                  0.)
    prsh = rshb + (rsho - rshb) * np.exp(-rshexp * g / go)
    return prsh


def filter_params(io, rsh, rs, ee, isc):
    # Function filter_params identifies bad parameter sets. A bad set contains
    # Nan, non-positive or imaginary values for parameters; Rs > Rsh; or data
    # where effective irradiance Ee differs by more than 5% from a linear fit
    # to Isc vs. Ee

    badrsh = np.logical_or(rsh < 0., np.isnan(rsh))
    negrs = rs < 0.
    badrs = np.logical_or(rs > rsh, np.isnan(rs))
    imagrs = ~(np.isreal(rs))
    badio = np.logical_or(~(np.isreal(rs)), io <= 0)
    goodr = np.logical_and(~badrsh, ~imagrs)
    goodr = np.logical_and(goodr, ~negrs)
    goodr = np.logical_and(goodr, ~badrs)
    goodr = np.logical_and(goodr, ~badio)

    matrix = np.vstack((ee / 1000., np.zeros(len(ee)))).T
    eff = np.linalg.lstsq(matrix, isc)[0][0]
    pisc = eff * ee / 1000
    pisc_error = np.abs(pisc - isc) / isc
    # check for departure from linear relation between Isc and Ee
    badiph = pisc_error > .05

    u = np.logical_and(goodr, ~badiph)
    return u


def check_converge(prevparams, result, vmp, imp, graphic, convergeparamsfig,
                   i):
    """
    Function check_converge computes convergence metrics for all IV curves.

    Parameters
    ----------
    prevparams: Convergence Parameters from the previous Iteration (used to
                determine Percent Change in values between iterations)
    result: performacne paramters of the (predicted) single diode fitting,
            which includes Voc, Vmp, Imp, Pmp and Isc
    vmp: measured values for each IV curve
    imp: measured values for each IV curve
    graphic: argument to determine whether to display Figures
    convergeparamsfig: Hangle to the ConvergeParam Plot
    i: Index of current iteration in cec_parameter_estimation

    Returns
    -------
    convergeparam: a class containing the following for Imp, Vmp and Pmp.
        - maximum percent difference between measured and modeled values
        - minimum percent difference between measured and modeled values
        - maximum absolute percent difference between measured and modeled
          values
        - mean percent difference between measured and modeled values
        - standard deviation of percent difference between measured and modeled
          values
        - absolute difference for previous and current values of maximum
          absolute percent difference (measured vs. modeled)
        - absolute difference for previous and current values of mean percent
          difference (measured vs. modeled)
        - absolute difference for previous and current values of standard
          deviation of percent difference (measured vs. modeled)

    """
    convergeparam = OrderedDict()

    imperror = (result['i_mp'] - imp) / imp * 100.
    vmperror = (result['v_mp'] - vmp) / vmp * 100.
    pmperror = (result['p_mp'] - (imp * vmp)) / (imp * vmp) * 100.

    convergeparam['imperrmax'] = max(imperror)  # max of the error in Imp
    convergeparam['imperrmin'] = min(imperror)  # min of the error in Imp
    # max of the absolute error in Imp
    convergeparam['imperrabsmax'] = max(abs(imperror))
    # mean of the error in Imp
    convergeparam['imperrmean'] = np.mean(imperror, axis=0)
    # std of the error in Imp
    convergeparam['imperrstd'] = np.std(imperror, axis=0, ddof=1)

    convergeparam['vmperrmax'] = max(vmperror)  # max of the error in Vmp
    convergeparam['vmperrmin'] = min(vmperror)  # min of the error in Vmp
    # max of the absolute error in Vmp
    convergeparam['vmperrabsmax'] = max(abs(vmperror))
    # mean of the error in Vmp
    convergeparam['vmperrmean'] = np.mean(vmperror, axis=0)
    # std of the error in Vmp
    convergeparam['vmperrstd'] = np.std(vmperror, axis=0, ddof=1)

    convergeparam['pmperrmax'] = max(pmperror)  # max of the error in Pmp
    convergeparam['pmperrmin'] = min(pmperror)  # min of the error in Pmp
    # max of the abs err. in Pmp
    convergeparam['pmperrabsmax'] = max(abs(pmperror))
    # mean error in Pmp
    convergeparam['pmperrmean'] = np.mean(pmperror, axis=0)
    # std error Pmp
    convergeparam['pmperrstd'] = np.std(pmperror, axis=0, ddof=1)

    if prevparams['state'] != 0.:
        convergeparam['imperrstdchange'] = \
            np.abs((convergeparam['imperrstd'] - prevparams['imperrstd']) /
                   prevparams['imperrstd'])
        convergeparam['vmperrstdchange'] = \
            np.abs((convergeparam['vmperrstd'] - prevparams['vmperrstd']) /
                   prevparams['vmperrstd'])
        convergeparam['pmperrstdchange'] = \
            np.abs((convergeparam['pmperrstd'] - prevparams['pmperrstd']) /
                   prevparams['pmperrstd'])
        convergeparam['imperrmeanchange'] = \
            np.abs((convergeparam['imperrmean'] - prevparams['imperrmean']) /
                   prevparams['imperrmean'])
        convergeparam['vmperrmeanchange'] = \
            np.abs((convergeparam['vmperrmean'] - prevparams['vmperrmean']) /
                   prevparams['vmperrmean'])
        convergeparam['pmperrmeanchange'] = \
            np.abs((convergeparam['pmperrmean'] - prevparams['pmperrmean']) /
                   prevparams['pmperrmean'])
        convergeparam['imperrabsmaxchange'] = \
            np.abs((convergeparam['imperrabsmax'] -
                    prevparams['imperrabsmax']) / prevparams['imperrabsmax'])
        convergeparam['vmperrabsmaxchange'] = \
            np.abs((convergeparam['vmperrabsmax'] -
                    prevparams['vmperrabsmax']) / prevparams['vmperrabsmax'])
        convergeparam['pmperrabsmaxchange'] = \
            np.abs((convergeparam['pmperrabsmax'] -
                    prevparams['pmperrabsmax']) / prevparams['pmperrabsmax'])
        convergeparam['state'] = 1.
    else:
        convergeparam['imperrstdchange'] = float("Inf")
        convergeparam['vmperrstdchange'] = float("Inf")
        convergeparam['pmperrstdchange'] = float("Inf")
        convergeparam['imperrmeanchange'] = float("Inf")
        convergeparam['vmperrmeanchange'] = float("Inf")
        convergeparam['pmperrmeanchange'] = float("Inf")
        convergeparam['imperrabsmaxchange'] = float("Inf")
        convergeparam['vmperrabsmaxchange'] = float("Inf")
        convergeparam['pmperrabsmaxchange'] = float("Inf")
        convergeparam['state'] = 1.

    if graphic:
        ax1 = convergeparamsfig.add_subplot(331)
        ax2 = convergeparamsfig.add_subplot(332)
        ax3 = convergeparamsfig.add_subplot(333)
        ax4 = convergeparamsfig.add_subplot(334)
        ax5 = convergeparamsfig.add_subplot(335)
        ax6 = convergeparamsfig.add_subplot(336)
        ax7 = convergeparamsfig.add_subplot(337)
        ax8 = convergeparamsfig.add_subplot(338)
        ax9 = convergeparamsfig.add_subplot(339)
        ax1.plot(i, convergeparam['pmperrmean'], 'x-')
        ax1.set_ylabel('mean((pPmp-Pmp)/Pmp*100)')
        ax1.set_title('Mean of Err in Pmp')
        ax1.hold(True)
        ax2.plot(i, convergeparam['vmperrmean'], 'x-')
        ax2.set_ylabel('mean((pVmp-Vmp)/Vmp*100)')
        ax2.set_title('Mean of Err in Vmp')
        ax2.hold(True)
        ax3.plot(i, convergeparam['imperrmean'], 'x-')
        ax3.set_ylabel('mean((pImp-Imp)/Imp*100)')
        ax3.set_title('Mean of Err in Imp')
        ax3.hold(True)
        ax4.plot(i, convergeparam['pmperrstd'], 'x-')
        ax4.set_ylabel('std((pPmp-Pmp)/Pmp*100)')
        ax4.set_title('Std of Err in Pmp')
        ax4.hold(True)
        ax5.plot(i, convergeparam['vmperrstd'], 'x-')
        ax5.set_ylabel('std((pVmp-Vmp)/Vmp*100)')
        ax5.set_title('Std of Err in Vmp')
        ax5.hold(True)
        ax6.plot(i, convergeparam['imperrstd'], 'x-')
        ax6.set_ylabel('std((pImp-Imp)/Imp*100)')
        ax6.set_title('Std of Err in Imp')
        ax6.hold(True)
        ax7.plot(i, convergeparam['pmperrabsmax'], 'x-')
        ax7.set_xlabel('Iteration')
        ax7.set_ylabel('max(abs((pPmp-Pmp)/Pmp*100))')
        ax7.set_title('AbsMax of Err in Pmp')
        ax7.hold(True)
        ax8.plot(i, convergeparam['vmperrabsmax'], 'x-')
        ax8.set_xlabel('Iteration')
        ax8.set_ylabel('max(abs((pVmp-Vmp)/Vmp*100))')
        ax8.set_title('AbsMax of Err in Vmp')
        ax8.hold(True)
        ax9.plot(i, convergeparam['imperrabsmax'], 'x-')
        ax9.set_xlabel('Iteration')
        ax9.set_ylabel('max(abs((pImp-Imp)/Imp*100))')
        ax9.set_title('AbsMax of Err in Imp')
        ax9.hold(True)
        plt.show()
    return convergeparam

const_default = OrderedDict()
const_default['E0'] = 1000.
const_default['T0'] = 25.
const_default['k'] = 1.38066e-23
const_default['q'] = 1.60218e-19


def fun_rsh(x, rshexp, ee, e0, rsh):
    tf = np.log10(estrsh(x, rshexp, ee, e0)) - np.log10(rsh)
    return tf


def pvsyst_parameter_estimation(ivcurves, specs, const=const_default,
                                maxiter=5, eps1=1.e-3, graphic=False):
    """
    pvsyst_parameter_estimation estimates parameters fro the PVsyst module
    performance model

    Syntax
    ------
    PVsyst, oflag = pvsyst_paramter_estimation(ivcurves, specs, const, maxiter,
                                               eps1, graphic)

    Description
    -----------
    pvsyst_paramter_estimation estimates parameters for the PVsyst module
    performance model [2,3,4]. Estimation methods are documented in [5,6,7].

    Parameters
    ----------
    ivcurves: a dict containing IV curve data in the following fields where j
    denotes the jth data set
        ivcurves['i'][j] - a numpy array of current (A) (same length as v)
        ivcurves['v'][j] - a numpy array of voltage (V) (same length as i)
        ivcurves['ee'][j] - effective irradiance (W / m^2), i.e., POA broadband
                            irradiance adjusted by solar spectrum modifier
        ivcurves['tc'][j] - cell temperature (C)
        ivcurves['isc'][j] - short circuit current of IV curve (A)
        ivcurves['voc'][j] - open circuit voltage of IV curve (V)
        ivcurves['imp'][j] - current at max power point of IV curve (A)
        ivcurves['vmp'][j] - voltage at max power point of IV curve (V)

    specs: a dict containing module-level values
        specs['ns'] - number of cells in series
        specs['aisc'] - temperature coefficeint of isc (A/C)

    const: an optional OrderedDict containing physical and other constants
        const['E0'] - effective irradiance at STC, normally 1000 W/m2
        constp['T0'] - cell temperature at STC, normally 25 C
        const['k'] - 1.38066E-23 J/K (Boltzmann's constant)
        const['q'] - 1.60218E-19 Coulomb (elementary charge)

    maxiter: an optional numpy array input that sets the maximum number of
             iterations for the parameter updating part of the algorithm.
             Default value is 5.

    eps1: the desired tolerance for the IV curve fitting. The iterative
          parameter updating stops when absolute values of the percent change
          in mean, max and standard deviation of Imp, Vmp and Pmp between
          iterations are all less than eps1, or when the number of iterations
          exceeds maxiter. Default value is 1e-3 (.0001%).

    graphic: a boolean, if true then plots are produced during the parameter
             estimation process. Default is false

    Returns
    -------
    pvsyst: a OrderedDict containing the model parameters
        pvsyst['IL_ref'] - light current (A) at STC
        pvsyst['Io_ref'] - dark current (A) at STC
        pvsyst['eG'] - effective band gap (eV) at STC
        pvsyst['Rsh_ref'] - shunt resistance (ohms) at STC
        pvsyst['Rsh0'] - shunt resistance (ohms) at zero irradiance
        pvsyst['Rshexp'] - exponential factor defining decrease in rsh with
                           increasing effective irradiance
        pvsyst['Rs_ref'] - series resistance (ohms) at STC
        pvsyst['gamma_ref'] - diode (ideality) factor at STC
        pvsyst['mugamma'] - temperature coefficient for diode (ideality) factor
        pvsyst['Iph'] - numpy array of values of light current Iph estimated
                        for each IV curve
        pvsyst['Io'] - numpy array of values of dark current Io estimated for
                       each IV curve
        pvsyst['Rsh'] - numpy array of values of shunt resistance Rsh estimated
                        for each IV curve
        pvsyst['Rs'] - numpy array of values of series resistance Rs estimated
                       for each IV curve
        pvsyst.u - filter indicating IV curves with parameter values deemed
                   reasonable by the private function filter_params

    oflag: Boolean indicating success or failure of estimation of the diode
           (ideality) factor parameter. If failure, then no parameter values
           are returned

    References
    ----------
    [1] PVLib MATLAB
    [2] K. Sauer, T. Roessler, C. W. Hansen, Modeling the Irradiance and
        Temperature Dependence of Photovoltaic Modules in PVsyst, IEEE Journal
        of Photovoltaics v5(1), January 2015.
    [3] A. Mermoud, PV Modules modeling, Presentation at the 2nd PV Performance
        Modeling Workshop, Santa Clara, CA, May 2013
    [4] A. Mermoud, T. Lejeuene, Performance Assessment of a Simulation Model
        for PV modules of any available technology, 25th European Photovoltaic
        Solar Energy Conference, Valencia, Spain, Sept. 2010
    [5] C. Hansen, Estimating Parameters for the PVsyst Version 6 Photovoltaic
        Module Performance Model, Sandia National Laboratories Report
        SAND2015-8598
    [6] C. Hansen, Parameter Estimation for Single Diode Models of Photovoltaic
        Modules, Sandia National Laboratories Report SAND2015-2065
    [7] C. Hansen, Estimation of Parameters for Single Diode Models using
        Measured IV Curves, Proc. of the 39th IEEE PVSC, June 2013.
    """
    ee = ivcurves['ee']
    tc = ivcurves['tc']
    tck = tc + 273.15
    isc = ivcurves['isc']
    voc = ivcurves['voc']
    imp = ivcurves['imp']
    vmp = ivcurves['vmp']

    # Cell Thermal Voltage
    vth = const['k'] / const['q'] * tck

    n = len(ivcurves['voc'])

    # Initial estimate of Rsh used to obtain the diode factor gamma0 and diode
    # temperature coefficient mugamma. Rsh is estimated using the co-content
    # integral method.

    pio = np.ones(n)
    piph = np.ones(n)
    prsh = np.ones(n)
    prs = np.ones(n)
    pn = np.ones(n)

    for j in range(n):
        current, voltage = rectify_iv_curve(ivcurves['i'][j], ivcurves['v'][j],
                                            voc[j], isc[j])
        # initial estimate of Rsh, from integral over voltage regression
        # [5] Step 3a; [6] Step 3a
        pio[j], piph[j], prs[j], prsh[j], pn[j] = \
            est_single_diode_param(current, voltage, vth[j] * specs['ns'])

    # Estimate the diode factor gamma from Isc-Voc data. Method incorporates
    # temperature dependence by means of the equation for Io

    y = np.log(isc - voc / prsh) - 3. * np.log(tck / (const['T0'] + 273.15))
    x1 = const['q'] / const['k'] * (1. / (const['T0'] + 273.15) - 1. / tck)
    x2 = voc / (vth * specs['ns'])
    t0 = np.isnan(y)
    t1 = np.isnan(x1)
    t2 = np.isnan(x2)
    uu = np.logical_or(t0, t1)
    uu = np.logical_or(uu, t2)

    x = np.vstack((np.ones(len(x1[~uu])), x1[~uu], -x1[~uu] *
                   (tck[~uu] - (const['T0'] + 273.15)), x2[~uu],
                   -x2[~uu] * (tck[~uu] - (const['T0'] + 273.15)))).T
    alpha = np.linalg.lstsq(x, y[~uu])[0]

    gamma_ref = 1. / alpha[3]
    mugamma = alpha[4] / alpha[3] ** 2

    if np.isnan(gamma_ref) or np.isnan(mugamma) or not np.isreal(gamma_ref) \
            or not np.isreal(mugamma):
        badgamma = True
    else:
        badgamma = False

    pvsyst = OrderedDict()

    if ~badgamma:
        gamma = gamma_ref + mugamma * (tc - const['T0'])

        if graphic:
            f1 = plt.figure()
            ax10 = f1.add_subplot(111)
            ax10.plot(x2, y, 'b+', x2, x * alpha, 'r.')
            ax10.set_xlabel('X = Voc / Ns * Vth')
            ax10.set_ylabel('Y = log(Isc - Voc/Rsh)')
            ax10.legend(['I-V Data', 'Regression Model'], loc=2)
            ax10.text(np.min(x2) + 0.85 * (np.max(x2) - np.min(x2)), 1.05 *
                      np.max(y), ['\gamma_0 = %s' % gamma_ref])
            ax10.text(np.min(x2) + 0.85 * (np.max(x2) - np.min(x2)), 0.98 *
                      np.max(y), ['\mu_\gamma = %s' % mugamma])
            plt.show()

        nnsvth = gamma * (vth * specs['ns'])

        # For each IV curve, sequentially determine initial values for Io, Rs,
        # and Iph [5] Step 3a; [6] Step 3

        io = np.ones(n)
        iph = np.ones(n)
        rs = np.ones(n)
        rsh = prsh

        for j in range(n):
            curr, volt = rectify_iv_curve(ivcurves['i'][j], ivcurves['v'][j],
                                          voc[j], isc[j])

            if rsh[j] > 0:
                # Initial estimate of Io, evaluate the single diode model at
                # voc and approximate Iph + Io = Isc [5] Step 3a; [6] Step 3b
                io[j] = (isc[j] - voc[j] / rsh[j]) * np.exp(-voc[j] /
                                                            nnsvth[j])

                # initial estimate of rs from dI/dV near Voc
                # [5] Step 3a; [6] Step 3c
                [didv, d2id2v] = numdiff(volt, curr)
                t3 = volt > .5 * voc[j]
                t4 = volt < .9 * voc[j]
                u = np.logical_and(t3, t4)
                tmp = -rsh[j] * didv - 1.
                v = np.logical_and(u, tmp > 0)
                if np.sum(v) > 0:
                    vtrs = nnsvth[j] / isc[j] * \
                           (np.log(tmp[v] * nnsvth[j] / (rsh[j] * io[j])) -
                            volt[v] / nnsvth[j])
                    rs[j] = np.mean(vtrs[vtrs > 0], axis=0)
                else:
                    rs[j] = 0.

                # Initial estimate of Iph, evaluate the single diode model at
                # Isc [5] Step 3a; [6] Step 3d

                iph[j] = isc[j] - io[j] + io[j] * np.exp(isc[j] / nnsvth[j]) \
                    + isc[j] * rs[j] / rsh[j]
            else:
                io[j] = float("Nan")
                rs[j] = float("Nan")
                iph[j] = float("Nan")

        # Filter IV curves for good initial values
        # [5] Step 3b
        u = filter_params(io, rsh, rs, ee, isc)

        # Refine Io to match Voc
        # [5] Step 3c
        tmpiph = iph
        tmpio = update_io_known_n(rsh[u], rs[u], nnsvth[u], io[u], tmpiph[u],
                                  voc[u])
        io[u] = tmpio

        # Calculate Iph to be consistent with Isc and current values of other
        # parameters [6], Step 3c
        iph = isc - io + io * np.exp(rs * isc / nnsvth) + isc * rs / rsh

        # Refine Rsh, Rs, Io and Iph in that order.
        counter = 1.  # counter variable for parameter updating while loop,
        # counts iterations
        prevconvergeparams = OrderedDict()
        prevconvergeparams['state'] = 0.

        if graphic:
            h = plt.figure()
        if graphic:
            # create a new handle for the converge parameter figure
            convergeparamsfig = plt.figure()

        t14 = np.array([True])

        while t14.any() and counter <= maxiter:
            # update rsh to match max power point using a fixed point method.
            tmprsh = update_rsh_fixed_pt(rsh[u], rs[u], io[u], iph[u],
                                         nnsvth[u], imp[u], vmp[u])

            if graphic:
                ax11 = h.add_subplot(111)
                ax11.plot(counter, np.mean(np.abs(tmprsh - rsh[u])), 'k')
                ax11.hold(True)
                ax11.set_xlabel('Iteration')
                ax11.set_ylabel('mean(abs(tmprsh[u] - rsh[u]))')
                ax11.set_title('Update Rsh')
                plt.show()

            rsh[u] = tmprsh

            # Calculate Rs to be consistent with Rsh and maximum power point
            [a, phi] = calc_theta_phi_exact(imp[u], iph[u], vmp[u], io[u],
                                            nnsvth[u], rs[u], rsh[u])
            rs[u] = (iph[u] + io[u] - imp[u]) * rsh[u] / imp[u] - \
                nnsvth[u] * phi / imp[u] - vmp[u] / imp[u]

            # Update filter for good parameters
            u = filter_params(io, rsh, rs, ee, isc)

            # Update value for io to match voc
            tmpio = update_io_known_n(rsh[u], rs[u], nnsvth[u], io[u], iph[u],
                                      voc[u])
            io[u] = tmpio

            # Calculate Iph to be consistent with Isc and other parameters
            iph = isc - io + io * np.exp(rs * isc / nnsvth) + isc * rs / rsh

            # update filter for good parameters
            u = filter_params(io, rsh, rs, ee, isc)

            # compute the IV curve from the current parameter values
            result = singlediode(iph[u], io[u], rs[u], rsh[u], nnsvth[u])

            # check convergence criteria
            # [5] Step 3d
            if graphic:
                convergeparams = check_converge(prevconvergeparams, result,
                                                vmp[u], imp[u], graphic,
                                                convergeparamsfig, counter)
            else:
                convergeparams = check_converge(prevconvergeparams, result,
                                                vmp[u], imp[u], graphic, 0.,
                                                counter)

            prevconvergeparams = convergeparams
            counter += 1.
            t5 = prevconvergeparams['vmperrmeanchange'] >= eps1
            t6 = prevconvergeparams['imperrmeanchange'] >= eps1
            t7 = prevconvergeparams['pmperrmeanchange'] >= eps1
            t8 = prevconvergeparams['vmperrstdchange'] >= eps1
            t9 = prevconvergeparams['imperrstdchange'] >= eps1
            t10 = prevconvergeparams['pmperrstdchange'] >= eps1
            t11 = prevconvergeparams['vmperrabsmaxchange'] >= eps1
            t12 = prevconvergeparams['imperrabsmaxchange'] >= eps1
            t13 = prevconvergeparams['pmperrabsmaxchange'] >= eps1
            t14 = np.logical_or(t5, t6)
            t14 = np.logical_or(t14, t7)
            t14 = np.logical_or(t14, t8)
            t14 = np.logical_or(t14, t9)
            t14 = np.logical_or(t14, t10)
            t14 = np.logical_or(t14, t11)
            t14 = np.logical_or(t14, t12)
            t14 = np.logical_or(t14, t13)

        # Extract coefficients for auxillary equations
        # Estimate Io0 and eG
        tok = const['T0'] + 273.15  # convert to to K
        x = const['q'] / const['k'] * (1. / tok - 1. / tck[u]) / gamma[u]
        y = np.log(io[u]) - 3. * np.log(tck[u] / tok)
        new_x = sm.add_constant(x)
        res = sm.RLM(y, new_x).fit()
        beta = res.params
        io0 = np.exp(beta[0])
        eg = beta[1]

        if graphic:
            # Predict Io and Eg
            pio = io0 * ((tc[u] + 273.15) / const['T0'] + 273.15) ** 3. * \
                  np.exp((const['q'] / const['k']) * (eg / gamma[u]) *
                         (1. / (const['T0'] + 273.15) - 1. / (tc[u] + 273.15)))

            iofig = plt.figure()
            ax12 = iofig.add_subplot(311)
            ax13 = iofig.add_subplot(312)
            ax14 = iofig.add_subplot(313)
            ax12.hold(True)
            ax12.plot(tc[u], y, 'r+', tc[u], beta[0] + x * beta[1], 'b.')
            ax12.set_xlabel('Cell temp. (C)')
            ax12.set_ylabel('log(Io)-3log(T_C/T_0)')
            ax12.legend(['Data', 'Model'], loc=2)
            ax13.hold(True)
            ax13.plot(tc[u], io[u], 'r+', tc[u], pio, '.')
            ax13.set_xlabel('Cell temp. (C)')
            ax13.set_ylabel('I_O (A)')
            ax13.legend(['Extracted', 'Predicted'], loc=2)
            ax14.hold(True)
            ax14.plot(tc[u], (pio - io[u]) / io[u] * 100., 'x')
            ax14.set_xlabel('Cell temp. (C)')
            ax14.set_ylabel('Percent Deviation in I_O')

            iofig1 = plt.figure()
            ax15 = iofig1.add_subplot(111)
            ax15.hold(True)
            ax15.plot(tc[u], y + 3. * (tc[u] / const['T0']), 'k.', tc[u],
                      beta[0] + x * beta[1] + 3 * (tc[u] / const['T0']), 'g.')
            ax15.set_xlabel('Cell temp. (C)')
            ax15.set_ylabel('log(Io)-3log(T_C/T_0)')
            ax15.legend(['Data', 'Regression Model'], loc=2)

            iofig2 = plt.figure()
            ax16 = iofig2.add_subplot(111)
            ax16.hold(True)
            ax16.plot(tc[u], io[u], 'b+', tc[u], pio, 'r.')
            ax16.set_xlabel('Cell temp. (C)')
            ax16.set_ylabel('I_O (A)')
            ax16.legend(['Extracted from IV Curves', 'Predicted by Eq. 3'],
                        loc=2)
            ax16.text(np.min(tc[u]), np.min(io[u]) + .83 *
                      (np.max(io[u]) - np.min(io[u])), ['I_{O0} = %s' % io0])
            ax16.text(np.min(tc[u]), np.min(io[u]) + .83 *
                      (np.max(io[u]) - np.min(io[u])), ['eG = %s' % eg])

        # Estimate Iph0
        x = tc[u] - const['T0']
        y = iph[u] * (const['E0'] / ee[u])
        # average over non-NaN values of Y and X
        nans = np.isnan(y - specs['aisc'] * x)
        iph0 = np.mean(y[~nans] - specs['aisc'] * x[~nans])

        if graphic:
            # Predict Iph
            piph = (ee[u] / const['E0']) * (iph0 + specs['aisc'] *
                                            (tc[u] - const['T0']))

            iphfig = plt.figure()
            ax17 = iphfig.add_subplot(311)
            ax18 = iphfig.add_subplot(312)
            ax19 = iphfig.add_subplot(313)
            ax17.hold(True)
            ax17.plot(ee[u], piph, 'r+', [0., np.max(ee[u])], [iph0, iph0])
            ax17.set_xlabel('Irradiance (W/m^2)')
            ax17.set_ylabel('I_L')
            ax17.legend(['Data', 'I_L at STC'], loc=4)
            ax18.hold(True)
            ax18.plot(ee[u], iph[u], 'r+', ee[u], piph, '.')
            ax18.set_xlabel('Irradiance (W/m^2)')
            ax18.set_ylabel('I_L (A)')
            ax18.legend(['Extracted', 'Predicted'], loc=2)
            ax19.hold(True)
            ax19.plot(ee[u], (piph - iph[u]) / iph[u] * 100., 'x',
                      [np.min(ee[u]), np.max(ee[u])], [0., 0.])
            ax19.set_xlabel('Irradiance (W/m^2)')
            ax19.set_ylabel('Percent Deviation from I_L')

            iphfig1 = plt.figure()
            ax20 = iphfig1.add_subplot(111)
            ax20.hold(True)
            ax20.plot(tc[u], iph[u], 'b+', tc[u], piph, 'r.', [0., 80.],
                      [iph0, iph0])
            ax20.set_xlabel('Cell temp. (C)')
            ax20.set_ylabel('I_L (W/m^2)')
            ax20.legend(['Extracted from IV Curves', 'Predicted by Eq. 2',
                         'I_L at STC'], loc=2)
            ax20.text(1.1 * np.min(tc[u]), 1.05 * iph0, ['I_{L0} = %s' % iph0])

        # Additional filter for Rsh and Rs; Restrict effective irradiance to be
        # greater than 400 W/m^2
        vfil = ee > 400

        # Estimate Rsh0, Rsh_ref and Rshexp

        # Initial Guesses. Rsh0 is value at Ee=0.
        nans = np.isnan(rsh)
        if any(ee < 400):
            grsh0 = np.mean(rsh[np.logical_and(~nans, ee < 400)])
        else:
            grsh0 = np.max(rsh)

        # Rsh_ref is value at Ee = 1000
        if any(vfil):
            grshref = np.mean(rsh[np.logical_and(~nans, vfil)])
        else:
            grshref = np.min(rsh)

        # PVsyst default for Rshexp is 5.5
        rshexp = 5.5

        # Here we use a nonlinear least squares technique. Lsqnonlin minimizes
        # the sum of squares of the objective function (here, tf).
        x0 = np.array([grsh0, grshref])
        beta = optimize.least_squares(fun_rsh, x0, args=(rshexp, ee[u],
                                                         const['E0'], rsh[u]),
                                      bounds=np.array([[1., 1.], [1.e7, 1.e6]])
                                      )

        # Extract PVsyst parameter values
        rsh0 = beta.x[0]
        rshref = beta.x[1]

        if graphic:
            # Predict Rsh
            prsh = estrsh(beta, rshexp, ee, const['E0'])

            rshfig = plt.figure()
            ax21 = rshfig.add_subplot(211)
            ax22 = rshfig.add_subplot(212)
            ax21.hold(True)
            ax21.plot(ee[u], np.log10(rsh[u]), 'r.', ee[u], np.log10(prsh[u]),
                      'b.')
            ax21.set_xlabel('Irradiance (W/m^2)')
            ax21.set_ylabel('log_{10}(R_{sh})')
            ax21.legend(['Extracted', 'Predicted'], loc=2)
            ax22.hold(True)
            ax22.plot(ee[u], (np.log10(prsh[u]) - np.log10(rsh[u])) /
                      np.log10(rsh[u]) * 100., 'x',
                      [np.min(ee[u]), np.max(ee[u])], [0., 0.])
            ax22.set_xlabel('Irradiance (W/m^2)')
            ax22.set_ylabel('Percent Deviation in log_{10}(R_{sh})')

            rshfig1 = plt.figure()
            ax23 = rshfig1.add_subplot(111)
            ax23.hold(True)
            ax23.plot(ee[u], np.log10(rsh[u]), 'b.', ee[u], np.log10(prsh[u]),
                      'r.')
            ax23.set_xlabel('Irradiance (W/m^2)')
            ax23.set_ylabel('log_{10}(R_{sh})')
            ax23.legend(['Extracted from IV Curves', 'Predicted by Eq. 5'],
                        loc=3)
            ax23.text(150, 3.65, ['R_{SH0} = %s' % rsh0])
            ax23.text(150, 3.5, ['R_{SH,ref} = %s' % rshref])
            ax23.text(150, 3.35, ['R_{SHexp} = %s' % rshexp])

        # Estimate Rs0
        t15 = np.logical_and(u, vfil)
        rs0 = np.mean(rs[t15])

        if graphic:
            rsfig = plt.figure()
            ax24 = rsfig.add_subplot(211)
            ax25 = rsfig.add_subplot(212)
            ax24.hold(True)
            ax24.plot(ee[t15], rs[t15], 'r.', ee[t15],
                      rs0 * np.ones(len(ee[t15])), 'b.')
            ax24.set_xlabel('Irradiance (W/m^2)')
            ax24.set_ylabel('R_S')
            ax24.legend(['R_S values', 'Model'])
            ax24.set_xlim([0, 1])
            ax24.set_ylin([0, 1200])
            ax25.hold(True)
            ax25.plot(ee[u], (rs0 - rs[u]) / rs[u] * 100., 'x',
                      [np.min(ee[u]), np.max(ee[u])], [0., 0.])
            ax25.set_xlabel('Irradiance (W/m^2)')
            ax25.set_ylabel('Percent Deviation in R_S')

            rsfig1 = plt.figure()
            ax26 = rsfig1.add_subplot(111)
            ax26.hold(True)
            ax26.plot(ee[t15], rs[t15], 'b.', [0., np.max(ee[u])], [rs0, rs0],
                      'r')
            ax26.set_xlabel('Irradiance (W/m^2)')
            ax26.set_ylabel('R_S')
            ax26.legend(['Extracted from IV Curves', 'Predicted by Eq. 7'],
                        loc=3)
            ax26.text(800, 1.2 * rs0, ['R_{S0} = %s' % rs0])

        # Save parameter estimates in output structure
        pvsyst['IL_ref'] = iph0
        pvsyst['Io_ref'] = io0
        pvsyst['eG'] = eg
        pvsyst['Rs_ref'] = rs0
        pvsyst['gamma_ref'] = gamma_ref
        pvsyst['mugamma'] = mugamma
        pvsyst['Iph'] = iph
        pvsyst['Io'] = io
        pvsyst['Rsh0'] = rsh0
        pvsyst['Rsh_ref'] = rshref
        pvsyst['Rshexp'] = rshexp
        pvsyst['Rs'] = rs
        pvsyst['Rsh'] = rsh
        pvsyst['Ns'] = specs['ns']
        pvsyst['u'] = u

        oflag = True
    else:
        oflag = False

        pvsyst['IL_ref'] = float("Nan")
        pvsyst['Io_ref'] = float("Nan")
        pvsyst['eG'] = float("Nan")
        pvsyst['Rs_ref'] = float("Nan")
        pvsyst['gamma_ref'] = float("Nan")
        pvsyst['mugamma'] = float("Nan")
        pvsyst['Iph'] = float("Nan")
        pvsyst['Io'] = float("Nan")
        pvsyst['Rsh0'] = float("Nan")
        pvsyst['Rsh_ref'] = float("Nan")
        pvsyst['Rshexp'] = float("Nan")
        pvsyst['Rs'] = float("Nan")
        pvsyst['Rsh'] = float("Nan")
        pvsyst['Ns'] = specs['ns']
        pvsyst['u'] = np.zeros(n)
    return pvsyst, oflag
