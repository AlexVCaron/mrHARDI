import argparse
import nibabel as nib
import numpy as np

from magic_monkey.b0_process import B0PostProcess, extract_b0


def get_parser():
    parser = argparse.ArgumentParser("Extract B0")
    parser.add_argument("dwi_in")
    parser.add_argument("bvals_in")
    parser.add_argument("b0_out")
    parser.add_argument("--strides", type=int, default=None)
    parser.add_argument("--mean", choices=["whole", "batch", "none"], default="none")

    return parser


def main():
    args = get_parser().parse_args()

    dwi_in = nib.load(args.dwi_in)
    bvals_in = np.loadtxt(args.bvals_in)

    b0_out = extract_b0(dwi_in, bvals_in, args.strides, B0PostProcess(args.mean))

    nib.save(nib.Nifti1Image(b0_out, dwi_in.affine, dwi_in.header), args.b0_out)
