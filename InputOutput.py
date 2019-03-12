import sys
import argparse
import re

import numpy as np
from numba import jit

import random
import warnings

def tryImportAlphaPlinkPython():
    alphaplinkpython_avail = False
    try:
        import alphaplinkpython
        from alphaplinkpython import PlinkWriter
        alphaplinkpython_avail = True

    except ImportError:
        warnings.warn("The module alphaplinkpython was not found. Plink files cannot be read in and will be ignored.")
    return alphaplinkpython_avail


##Global: 
args = None



def getParser(program) :
    parser = argparse.ArgumentParser(description='')
    core_parser = parser.add_argument_group("Core arguments")
    core_parser.add_argument('-out', required=True, type=str, help='The output file prefix.')

    addInputFileParser(parser)

    #Genotype files.
    output_options_parser = parser.add_argument_group("Output options")

    output_options_parser.add_argument('-writekey', default="id", required=False, type=str, help='Determines the order in which individuals are ordered in the output file based on their order in the corresponding input file. Animals not in the input file are placed at the end of the file and sorted in alphanumeric order. These animals can be surpressed with the "-onlykeyed" option. Options: id, pedigree, genotypes, sequence, segregation. Defualt: id.')
    output_options_parser.add_argument('-onlykeyed', action='store_true', required=False, help='Flag to surpress the animals who are not present in the file used with -outputkey. Also surpresses "dummy" animals.')
    
    if program == "AlphaImpute" :
        core_impute_parser = parser.add_argument_group("Impute options")
        core_impute_parser.add_argument('-no_impute', action='store_true', required=False, help='Flag to read in the files but not perform imputation.')
        core_impute_parser.add_argument('-no_phase', action='store_true', required=False, help='Flag to not do HD phasing initially.')
        core_impute_parser.add_argument('-maxthreads',default=1, required=False, type=int, help='Number of threads to use. Default: 1.')
        core_impute_parser.add_argument('-binaryoutput', action='store_true', required=False, help='Flag to write out the genotypes as a binary plink output.')

    if program in ["AlphaPeel", "AlphaAssign", "AlphaMGS", "AlphaCall"]:
        prob_parser = parser.add_argument_group("Genotype probability arguments")

        prob_parser.add_argument('-error', default=0.01, required=False, type=float, help='Genotyping error rate. [Default 0.01]')
        prob_parser.add_argument('-seqerror', default=0.001, required=False, type=float, help='Assumed sequencing error rate. [Default 0.001]')
    
    if program in ["longreads"]:
        longread_parser = parser.add_argument_group("Long read arguments")
        longread_parser.add_argument('-longreads', default=None, required=False, type=str, nargs="*", help='A read file.')

    if program == "AlphaPeel" :
        core_peeling_parser = parser.add_argument_group("Mandatory peeling arguments")
        core_peeling_parser.add_argument('-runtype', default=None, required=False, type=str, help='Program run type. Either "single" or "multi".')

        peeling_parser = parser.add_argument_group("Optional peeling arguments")

        peeling_parser.add_argument('-ncycles',default=5, required=False, type=int, help='Number of peeling cycles. Default: 5.')
        peeling_parser.add_argument('-maxthreads',default=1, required=False, type=int, help='Number of threads to use. Default: 1.')
        peeling_parser.add_argument('-length', default=1.0, required=False, type=float, help='Estimated length of the chromosome in Morgansa. [Default 1.00]')
        peeling_parser.add_argument('-penetrance',   default=None, required=False, type=str, nargs="*", help='An optional external penetrance file. This will overwrite the default penetrance values.')

        peeling_control_parser = parser.add_argument_group("Peeling control arguments")
        peeling_control_parser.add_argument('-esterrors', action='store_true', required=False, help='Flag to re-estimate the genotyping error rates after each peeling cycle.')
        peeling_control_parser.add_argument('-estmaf', action='store_true', required=False, help='Flag to re-estimate the minor allele frequency after each peeling cycle.')
        # peeling_control_parser.add_argument('-esttransitions', action='store_true', required=False, help='Flag to re-estimate the transmission rates after each peeling cycle. Currently not recommended to use')
        peeling_control_parser.add_argument('-nophasefounders', action='store_true', required=False, help='A flag phase a heterozygous allele in one of the founders (if such an allele can be found).')
        peeling_control_parser.add_argument('-sexchrom', action='store_true', required=False, help='A flag to that this is a sex chromosome. Sex needs to be given in the pedigree file. This is currently an experimental option.')

        singleLocus_parser = parser.add_argument_group("Single locus arguments")

        singleLocus_parser.add_argument('-mapfile',default=None, required=False, type=str, help='a map file for genotype data.')
        singleLocus_parser.add_argument('-segmapfile',default=None, required=False, type=str, help='a map file for the segregation estimates for hybrid peeling.')
        singleLocus_parser.add_argument('-segfile',default=None, required=False, type=str, help='A segregation file for hybrid peeling.')
        # singleLocus_parser.add_argument('-blocksize',default=100, required=False, type=int, help='The number of markers to impute at once. This changes the memory requirements of the program.')

        output_parser = parser.add_argument_group("Peeling output options")
        
        output_parser.add_argument('-no_dosages', action='store_true', required=False, help='Flag to surpress the dosage files.')
        output_parser.add_argument('-no_seg', action='store_true', required=False, help='Flag to surpress the segregation files (e.g. when running for chip imputation and not hybrid peeling).')
        output_parser.add_argument('-no_params', action='store_true', required=False, help='Flag to surpress writing the paramater files.')

        output_parser.add_argument('-haps', action='store_true', required=False, help='Flag to enable writing out the genotype probabilities.')
        output_parser.add_argument('-calling_threshold', default=None, required=False, type=float, nargs="*", help='Genotype calling threshold(s). Multiple space seperated vallues allowed. Use. .3 for best guess genotype.')
        output_parser.add_argument('-binary_call_files', action='store_true', required=False, help='Flag to write out the called genotype files as a binary plink output [Not yet implimented].')

    if program == "AlphaPlantImpute" :
        core_plant_parser = parser.add_argument_group("Mandatory arguments")
        core_plant_parser.add_argument('-plantinfo', default=None, required=False, type=str, nargs="*", help='A plant info file.')

    
    if program == "AlphaAssign" :
        core_assign_parser = parser.add_argument_group("Core assignement arguments")

        core_assign_parser.add_argument('-potentialsires', default=None, required=False, type=str, help='A list of potential sires for each individual.')
        core_assign_parser.add_argument('-potentialdams', default=None, required=False, type=str, help='A list of potential dams for each individual.')
        core_assign_parser.add_argument('-checkpedigree', action='store_true', required=False, help='Flag to check the pre-existing pedigree.')
        core_assign_parser.add_argument('-assignall',action='store_true', required=False, help='Flag to force the algorithm to assign a sire. Does not effect the -checkpedigree option. Recomended only if the true sire/dam is guaranteed to be in the list of putative parents.')
        


        assign_parser = parser.add_argument_group("Additional assignment arguments")
        #Additional options.

        assign_parser.add_argument('-snplist',default=None, required=False, type=str, help='An optional list of SNPs to use for parentage assignement and pedigree reconstruction. Only works if a bfile is included.')
        assign_parser.add_argument('-subsample',default="all", required=False, type=str, help='How should markers be subsetted? [all, coverage]')
        
        assign_parser.add_argument('-usemaf', action='store_true', required=False, help='A flag to use the minor allele frequency when constructing genotype estimates for the sire and maternal grandsire. Not recomended for small input pedigrees.')

        selection_parser = parser.add_argument_group("Arguments to choose how sires and dams are assigned")
        selection_parser.add_argument('-runtype',default="both", required=False, type=str, help='opp, likelihood, both')
        selection_parser.add_argument('-add_threshold',default=9, required=False, type=float, help='Assignement score threshold for adding a new individual as a parent')
        selection_parser.add_argument('-remove_threshold',default=-9, required=False, type=float, help='Assignement score threshold for removing an existing parent')
        selection_parser.add_argument('-p_threshold',default=-9, required=False, type=float, help='Negative log-pvalue threshold for removing parents via opposing homozygotes')
    
    if program == "AlphaMGS" :
        core_assign_parser = parser.add_argument_group("Core assignement arguments")
        core_assign_parser.add_argument('-potentialgrandsires', default=None, required=False, type=str, help='A list of potential dams for each individual.')
        core_assign_parser.add_argument('-usemaf', action='store_true', required=False, help='A flag to use the minor allele frequency when constructing genotype estimates for the sire and maternal grandsire. Not recomended for small input pedigrees.')

    if program == "AlphaCall":
        call_parser = parser.add_argument_group("AlphaCall arguments")
        call_parser.add_argument('-threshold', default=None, required=False, type=float, help='Genotype calling threshold. Use. .3 for best guess genotype.')
        call_parser.add_argument('-sexchrom', action='store_true', required=False, help='A flag to that this is a sex chromosome. Sex needs to be given in the pedigree file. This is currently an experimental option.')

    return parser


def addInputFileParser(parser):
    genotype_parser = parser.add_argument_group("Input arguments")

    genotype_parser.add_argument('-bfile',   default=None, required=False, type=str, nargs="*", help='A file in plink (binary) format (only stable on Linux).')
    genotype_parser.add_argument('-genotypes', default=None, required=False, type=str, nargs="*", help='A file in AlphaGenes format.')
    genotype_parser.add_argument('-reference', default=None, required=False, type=str, nargs="*", help='A haplotype reference panel in AlphaGenes format.')
    genotype_parser.add_argument('-seqfile', default=None, required=False, type=str, nargs="*", help='A sequence data file.')
    genotype_parser.add_argument('-pedigree',default=None, required=False, type=str, nargs="*", help='A pedigree file in AlphaGenes format.')
    genotype_parser.add_argument('-phasefile',default=None, required=False, type=str, nargs="*", help='A phase file in AlphaGenes format.')
    genotype_parser.add_argument('-startsnp',default=None, required=False, type=int, help='The first marker to consider. The first marker in the file is marker "1".')
    genotype_parser.add_argument('-stopsnp',default=None, required=False, type=int, help='The last marker to consider.')
    genotype_parser.add_argument('-seed',default=None, required=False, type=int, help='A random seed to use for debugging.')


def parseArgs(program, parser = None):
    global args
    args = rawParseArgs(program, parser)
    args.program = program

    if args.startsnp is not None:
        args.startsnp -= 1
        args.stopsnp -= 1
    ##Add any necessary code to check args here.
    return args

def rawParseArgs(program, parser = None) :
    if parser is None:
        parser = getParser(program)

    args = sys.argv[1:]
    if len(args) == 0 : 
        parser.print_help(sys.stderr)
        sys.exit(1)

    
    if len(args) == 1:
        with open(args[0]) as f:
            args = []
            for line in f:
                if line[0] != "-": line = "-" + line
                args.extend(re.split(r"[,|\s|\n]+",line))
    for arg in args:
        if len(arg) == 0:
            args.remove(arg)

    for i, arg in enumerate(args):
        if len(arg) > 0 and arg[0] == "-":
            args[i] = str.lower(arg)

    return parser.parse_args(args)


@jit(nopython=True)
def setNumbaSeeds(seed):
    np.random.seed(seed)
    random.seed(seed)

def readInPedigreeFromInputs(pedigree, args, genotypes = True, haps = False, reads = False) :
    if args.seed is not None:
        np.random.seed(args.seed)
        random.seed(args.seed)
        setNumbaSeeds(args.seed)


    pedigree.args = args
    pedigreeReadIn = False
    if args.pedigree is not None: 
        pedigreeReadIn = True
        for ped in args.pedigree:
            pedigree.readInPedigree(ped)

    
    if args.genotypes is not None: 
        for geno in args.genotypes:
            pedigree.readInGenotypes(geno, args.startsnp, args.stopsnp)
    
    if args.reference is not None: 
        for ref in args.reference:
            pedigree.readInReferencePanel(ref, args.startsnp, args.stopsnp)
    
    if args.seqfile is not None: 
        for seq in args.seqfile:
            pedigree.readInSequence(seq, args.startsnp, args.stopsnp)
    
    if args.phasefile is not None: 
        if args.program == "AlphaPeel":
            print("Use of an external phase file is not currently supported. Phase information will be translated to genotype probabilities. If absolutely necessary use a penetrance file instead.") 
        for phase in args.phasefile:
            pedigree.readInPhase(phase, args.startsnp, args.stopsnp)
    
    if args.bfile is not None: 
        alphaplinkpython_avail = tryImportAlphaPlinkPython()

        if alphaplinkpython_avail:
            for plink in args.bfile:
                if pedigreeReadIn == True:
                    print(f"Pedigree file read in from -pedigree option. Reading in binary plink file {plink}. Pedigree information in the .fam file will be ignored.")
                readInGenotypesPlink(pedigree, plink, args.startsnp, args.stopsnp, pedigreeReadIn)

    #It's important that these happen after all the datafiles are read in.
    #Each read in can add individuals. This information needs to be calculated on the final pedigree.
    pedigree.fillIn(genotypes, haps, reads)
    pedigree.setUpGenerations()
    pedigree.setupFamilies()

def readMapFile(mapFile, start = None, stop = None) :
    ids = []
    chrs = []
    positions = []
    with open(mapFile) as f:
        for line in f:
            parts = line.split(); 
            try:
                positions.append(float(parts[2]))
                chrs.append(parts[1])
                ids.append(parts[0])
            except ValueError:
                pass

    if start is None:
        start = 0
        stop = len(ids)

    return (ids[start:stop], chrs[start:stop], positions[start:stop])


# def getPositionsFromMap(mapFileName, nLoci) :
#     if mapFileName is None:
#         return np.arange(nLoci, dtype = np.float32)

#     positions = []
#     with open(mapFileName) as f:
#         for line in f:
#             parts = line.split(); 
#             try:
#                 positions.append(float(parts[1]))
#             except ValueError:
#                 pass
#     if len(positions) != nLoci :
#         raise ValueError(f"Number of loci not equal to map file length {nLoci}, {len(positions)}")

#     return np.array(positions, dtype = np.float32)


def readInSeg(pedigree, fileName, start=None, stop = None):
    print("Reading in seg file:", fileName)
    if start is None: start = 0
    if stop is None: stop = pedigree.nLoci
    nLoci = stop - start + 1 #Contains stop.
    


    print(pedigree.maxIdn)
    seg = np.full((pedigree.maxIdn, 4, nLoci), .25, dtype = np.float32)
    index = 0

    fileNColumns = 0

    indHit = np.full(pedigree.maxIdn, 0, dtype = np.int64)

    with open(fileName) as f:
        e = 0
        currentInd = None
        for line in f:
            parts = line.split();
            idx = parts[0]; 

            if fileNColumns == 0:
                fileNColumns = len(parts)
            if fileNColumns != len(parts):
                raise ValueError(f"The length of the line is not the expected length. Expected {fileNColumns} got {len(parts)} on individual {idx} and line {e}.")

            segLine=np.array([float(val) for val in parts[(start+1):(stop+2)]], dtype = np.float32)
            if len(segLine) != nLoci:
                raise ValueError(f"The length of the line subsection is not the expected length. Expected {nLoci} got {len(segLine)} on individual {idx} and line {e}.")

            if idx not in pedigree.individuals:
                print(f"Individual {idx} not found in pedigree. Individual ignored.")
            else:
                ind = pedigree.individuals[idx]
                if e == 0: 
                    currentInd = ind.idx
                if currentInd != ind.idx:
                    raise ValueError(f"Unexpected individual. Expecting individual {currentInd}, but got ind {ind.idx} on value {e}")
                seg[ind.idn,e,:] = segLine
                e = (e+1)%4
                ind.fileIndex['segregation'] = index; index += 1
                indHit[ind.idn] += 1
        for ind in pedigree:
            if indHit[ind.idn] != 4:
                print(f"No segregation information found for individual {ind.idx}")

    return seg


def writeIdnIndexedMatrix(pedigree, matrix, outputFile):
    np.set_printoptions(suppress=True)
    print("Writing to ", outputFile)
    with open(outputFile, 'w+') as f:

        for idx, ind in pedigree.writeOrder():
            if len(matrix.shape) == 2 :
                tmp = np.around(matrix[ind.idn, :], decimals = 4)
                f.write(' '.join(map(str, tmp)))
                # f.write('\n')
            if len(matrix.shape) == 3 :
                for i in range(matrix.shape[1]) :
                    f.write(idx + " ")
                    tmp2 = map("{:.4f}".format, matrix[ind.idn,i, :].tolist())
                    tmp3 = ' '.join(tmp2)
                    f.write(tmp3)
                    f.write('\n')
                # f.write('\n')
def writeFamIndexedMatrix(pedigree, matrix, outputFile):
    np.set_printoptions(suppress=True)
    print("Writing to ", outputFile)
    with open(outputFile, 'w+') as f:

        for fam in pedigree.getFamilies():
            if len(matrix.shape) == 2 :
                tmp = np.around(matrix[fam.idn, :], decimals = 4)
                f.write(' '.join(map(str, tmp)))
                # f.write('\n')
            if len(matrix.shape) == 3 :
                for i in range(matrix.shape[1]) :
                    f.write(str(fam.idn) + " ")
                    tmp2 = map("{:.4f}".format, matrix[fam.idn,i, :].tolist())
                    tmp3 = ' '.join(tmp2)
                    f.write(tmp3)
                    f.write('\n')
                # f.write('\n')

def writeOutGenotypesPlink(pedigree, fileName):

    alphaplinkpython_avail = tryImportAlphaPlinkPython()
    print("avial", alphaplinkpython_avail)
    if alphaplinkpython_avail:
        import alphaplinkpython
        from alphaplinkpython import PlinkWriter

        ped = [getFamString(ind) for ind in pedigree]

        nLoci = pedigree.nLoci
        nInd = len(pedigree.individuals)
        genotypes = np.full((nLoci, nInd), 0, dtype = np.int8)

        for i, ind in enumerate(pedigree):
            genotypes[:,i] = ind.genotypes

        genotypeIds = ["snp" + str(i+1) for i in range(nLoci)]
        genotypePos = [i + 1 for i in range(nLoci)]
        if args.startsnp is not None:
            genotypeIds = ["snp" + str(i + args.startsnp + 1) for i in range(nLoci)]
            genotypePos = [i + args.startsnp + 1 for i in range(nLoci)]

        PlinkWriter.writeFamFile(fileName + ".fam", ped)
        # PlinkWriter.writeBimFile(genotypeIds, fileName + ".bim")
        writeSimpleBim(genotypeIds, genotypePos, fileName + ".bim")
        PlinkWriter.writeBedFile(genotypes, fileName + ".bed")

def writeSimpleBim(genotypeIds, genotypePos, fileName) :
    with open(fileName, "w") as file:
        for i in range(len(genotypeIds)):
            line = f"1 {genotypeIds[i]} 0 {genotypePos[i]} A B \n"
            file.write(line)



def readInGenotypesPlink(pedigree, fileName, startsnp, endsnp, externalPedigree = False):
    bim = PlinkWriter.readBimFile(fileName + '.bim')
    fam = PlinkWriter.readFamFile(fileName + '.fam')
    bed = PlinkWriter.readBedFile(fileName + '.bed', bim, fam)
    if startsnp is not None:
        bed = bed[startsnp:endsnp,:]

    pedList = [[line.getId(), line.getSire(), line.getDam()] for line in fam]
    idList = [line.getId() for line in fam]

    pedigree.readInFromPlink(idList, pedList, bed, externalPedigree)


def getFamString(ind):
    sireStr = 0
    damStr = 0
    if ind.sire is not None:
        sireStr = ind.sire.idx
    if ind.dam is not None:
        damStr = ind.dam.idx

    return [str(ind.idx), str(sireStr), str(damStr)]
    # return [str(ind.idx).encode('utf-8'), str(sireStr).encode('utf-8'), str(damStr).encode('utf-8')]

# @profile
# def writeIdnIndexedMatrix2(pedigree, matrix, outputFile):
#     np.set_printoptions(suppress=True)
#     print("Writing to ", outputFile)
#     with open(outputFile, 'w+') as f:

#         for idx, ind in pedigree.individuals.items():
#             if len(matrix.shape) == 2 :
#                 tmp = np.around(matrix[ind.idn, :], decimals = 4)
#                 f.write(' '.join(map(str, tmp)))
#                 f.write('\n')
#             if len(matrix.shape) == 3 :
#                 for i in range(matrix.shape[1]) :
#                     tmp2 = tuple(map("{:.4f}".format, matrix[ind.idn,i, :]))
#                     tmp3 = ' '.join(tmp2)
#                     f.write(tmp3)
#                     f.write('\n')

