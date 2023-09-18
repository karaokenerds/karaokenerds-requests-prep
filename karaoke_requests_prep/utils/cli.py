#!/usr/bin/env python
import argparse
import logging
import pkg_resources
from karaoke_requests_prep import KaraokeNerdsRequestsPrep


def main():
    logger = logging.getLogger(__name__)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter(fmt="%(asctime)s.%(msecs)03d - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    parser = argparse.ArgumentParser(
        description="Fetch audio and lyrics for requests from karaokenerds, to prepare for bulk karaoke video creation.",
        formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=50),
    )

    parser.add_argument("limit", nargs="?", help="Number of requests to fetch.", default=argparse.SUPPRESS)

    package_version = pkg_resources.get_distribution("karaokenerds-requests-prep").version
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {package_version}")

    parser.add_argument(
        "--log_level",
        default="info",
        help="Optional: logging level, e.g. info, debug, warning (default: %(default)s). Example: --log_level=debug",
    )

    parser.add_argument(
        "--model_name",
        default="UVR_MDXNET_KARA_2",
        help="Optional: model name to be used for separation (default: %(default)s). Example: --model_name=UVR-MDX-NET-Inst_HQ_3",
    )

    parser.add_argument(
        "--model_file_dir",
        default="/tmp/audio-separator-models/",
        help="Optional: model files directory (default: %(default)s). Example: --model_file_dir=/app/models",
    )

    parser.add_argument(
        "--output_dir",
        default="karaoke",
        help="Optional: directory to write output files (default: <current dir>/karaoke). Example: --output_dir=/app/karaoke",
    )

    parser.add_argument(
        "--use_cuda",
        action="store_true",
        help="Optional: use Nvidia GPU with CUDA for separation (default: %(default)s). Example: --use_cuda=true",
    )

    parser.add_argument(
        "--use_coreml",
        action="store_true",
        help="Optional: use Apple Silicon GPU with CoreML for separation (default: %(default)s). Example: --use_coreml=true",
    )

    parser.add_argument(
        "--denoise",
        type=lambda x: (str(x).lower() == "true"),
        default=True,
        help="Optional: enable or disable denoising during separation (default: %(default)s). Example: --denoise=False",
    )

    parser.add_argument(
        "--normalize",
        type=lambda x: (str(x).lower() == "true"),
        default=True,
        help="Optional: enable or disable normalization during separation (default: %(default)s). Example: --normalize=False",
    )

    parser.add_argument(
        "--create_track_subfolders",
        action="store_true",
        help="Optional: create subfolders in the output folder for each track (default: %(default)s). Example: --create_track_subfolders=true",
    )

    # Add an argument to skip the first X number of results
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Optional: skip the first X number of results. Example: --skip=10",
    )

    # Add an argument to choose the order for the "sort" URL parameter
    valid_sort_options = ["votes", "tip", "views", "spotify", "date"]
    parser.add_argument(
        "--sort",
        choices=valid_sort_options,
        default="votes",
        help="Optional: choose the order for the sort parameter (default: %(default)s). Valid options: " + ", ".join(valid_sort_options),
    )

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)

    if not hasattr(args, "limit"):
        parser.print_help()
        exit(1)

    logger.info(f"RequestsPrep beginning with limit: {args.limit}")

    kprep = KaraokeNerdsRequestsPrep(
        limit=args.limit,
        log_formatter=log_formatter,
        log_level=log_level,
        model_name=args.model_name,
        model_file_dir=args.model_file_dir,
        output_dir=args.output_dir,
        use_cuda=args.use_cuda,
        use_coreml=args.use_coreml,
        normalization_enabled=args.normalize,
        denoise_enabled=args.denoise,
        create_track_subfolders=args.create_track_subfolders,
        skip_num=args.skip,
        sort_order=args.sort,
    )
    output_files = kprep.prep()

    logger.info(f"KaraokeNerds Requests Prep complete! Output files:")

    for artist_title, track in output_files.items():
        logger.info(f"")
        logger.info(f"Track: {artist_title} ({track['votes']} votes)")
        logger.info(f" YouTube Audio: {track['youtube_audio']}")
        logger.info(f" Lyrics: {track['lyrics']}")
        logger.info(f" Instrumental: {track['instrumental_audio']}")
        logger.info(f" Vocals: {track['vocals_audio']}")


if __name__ == "__main__":
    main()
