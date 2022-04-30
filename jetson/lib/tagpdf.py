import argparse
from functools import cached_property
import itertools
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

MIN_MARGIN=18
TEXT_HEIGHT=36

def assign_tags_to_pages(tag_ids, tags_per_page, repeat):
    if repeat:
        return [
            [tag_id] * tags_per_page
            for tag_id in tag_ids
        ]
    else:
        return [
            list(g)
            for (k, g) in itertools.groupby(
                tag_ids,
                key=lambda x: (x - tag_ids[0]) // tags_per_page,
            )
        ]

def scale_images(tags_root, tag_ids, scale):
    tmp_dir = tempfile.mkdtemp()
    filenames=[f"{tags_root}/tagStandard41h12/tag41_12_{tag_id:05}.png" for tag_id in tag_ids]
    with open(os.path.join(tmp_dir, "files.txt"), 'wt') as f:
        for fn in filenames:
            f.write(fn+'\n')
    cmd = [
        "convert", 
        f"@{tmp_dir}/files.txt",
        "-scale",
        f"{scale*100}%",
        f"{tmp_dir}/image-%d.png"
    ]
    subprocess.run(cmd, check=True)

    return {tag_id: f"{tmp_dir}/image-{i}.png" for (i, tag_id) in enumerate(tag_ids)}


class PageLayout:
    def __init__(self, rows, columns, width, height):
        self.rows = rows
        self.columns = columns
        self.width = width
        self.height=height
    
    @cached_property
    def scale(self):
        # The TEXT_HEIGHT here is the height of space we want to preserve for putting the
        # tag id under the tag (in px).
        max_cell_width = (self.width-(self.columns-1)*MIN_MARGIN)//self.columns
        max_cell_height = (self.height-(self.rows*TEXT_HEIGHT)-(self.rows-1)*MIN_MARGIN)//self.rows

        return min(max_cell_width//9, max_cell_height//9)


    def page_svg(self, tags, tag_img_map):
            # The tag images themselves are 9x9 px and we want to scale up by an integer
            # to avoid dithering/antialiasing:
            cell_dim = 9*self.scale
            cell_box_height = cell_dim+TEXT_HEIGHT
            horiz_margin = (self.width-(cell_dim*self.columns))//self.columns
            vert_margin = (self.height-(cell_box_height*self.rows))//self.rows

            # print("horiz_margin", horiz_margin)
            # print("vert_margin", vert_margin)

            doc=ET.Element(
                'svg',
                width=f"{self.width}px",
                height=f"{self.height}px",
                xmlns='http://www.w3.org/2000/svg'
            )

            for (i, tag_id) in enumerate(tags):
                row = i//self.columns
                col = i%self.columns

                doc.append(ET.Element(
                    'image',
                    href=f'file://{tag_img_map[tag_id]}',
                    x=f'{col*(cell_dim+horiz_margin)}px',
                    y=f'{row*(cell_box_height+vert_margin)}px',
                    width=f'{cell_dim}px',
                    height=f'{cell_dim}px',
                    # style="image-rendering: pixelated;"
                    # attrib={"image-rendering": "pixelated"}
                ))
                # 16 below is a fudge factor so the labels are approximately centered
                text_elt = ET.Element(
                    'text',
                    x=f'{col*(cell_dim+horiz_margin)+cell_dim//2-16}px',
                    y=f'{row*(cell_box_height+vert_margin)+cell_dim+TEXT_HEIGHT/2}px',
                )
                text_elt.text=f'{tag_id:05}'
                doc.append(text_elt)

            return doc



def main():
    parser = argparse.ArgumentParser(description="""
    Generates a PDF with multiple pages of april tags. Requires
    the repo at https://github.com/AprilRobotics/apriltag-imgs to be
    available locally--specify the path using either the APRILTAG_IMGS
    environment variable or the --tags-root flag.
    """)
    parser.add_argument("first_tag_id", type=int, help="First tag id to use.")
    parser.add_argument("last_tag_id", type=int, help="Last tag id to use.")
    parser.add_argument("output_file", help="Name of output file.")
    parser.add_argument("--tags-root", help="Path to directory where apriltag-imgs repo is cloned. Uses APRILTAG_IMGS variable otherwise.", default=os.getenv('APRILTAG_IMGS'))
    parser.add_argument(
        "-o", "--orientation", choices=("landscape", "portrait"), default="landscape"
    )
    parser.add_argument(
        "-c",
        "--columns",
        type=int,
        default=3,
        help="Number of columns of tags per page.",
    )
    parser.add_argument(
        "-r", "--rows", type=int, default=2, help="Number of rows of tags per page."
    )
    parser.add_argument(
        "--repeat",
        action="store_true",
        help="Use one tag id per page, repeating tag to fill.",
    )
    parser.add_argument(
        "--open", action="store_true", help="Open file after generating."
    )
    args = parser.parse_args()

    if args.tags_root is None:
        sys.exit("Root of apriltag-imgs repo must be specified using --tags-root or APRILTAG_IMGS variable.")
    
    page_dim = {"portrait": (612, 792), "landscape": (792, 612)}[args.orientation]

    tag_ids = list(range(args.first_tag_id, args.last_tag_id+1))
    layout = PageLayout(args.rows, args.columns, page_dim[0]-72, page_dim[1]-72)
    tag_img_map = scale_images(args.tags_root, tag_ids, layout.scale)

    tmp_dir = tempfile.mkdtemp()
    for (pageno, page_tags) in enumerate(assign_tags_to_pages(tag_ids, args.columns*args.rows, args.repeat)):
        # print(ET.tostring(page_svg(page_tags, args.rows, args.columns, args.orientation)))
        with open(os.path.join(tmp_dir, f'page-{pageno}.svg'), 'wb') as f:
            f.write(ET.tostring(layout.page_svg(page_tags, tag_img_map)))

    cmd = [
        "convert",
        f"{tmp_dir}/*.svg",
        "-gravity", "center",
        "-extent", f"{page_dim[0]}x{page_dim[1]}",
        args.output_file
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
