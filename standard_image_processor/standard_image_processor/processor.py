import json
import os
import re

import PIL.Image
import boto3
import numpy as np
from base_processor.imaging import utils, BaseImageProcessor
from botocore.client import Config
from base_processor.imaging.deepzoom import ImageCreator, DeepZoomImageDescriptor, _get_or_create_path, _get_files_path


PIL.Image.MAX_IMAGE_PIXELS = None


class StandardImageOutputFile(object):
    def __init__(self, *args, **kwargs):
        self.file_path = None
        self.view_path = None
        self.file_format = None
        self.view_format = 'png'

        self.img_data_shape = None
        self.img_dimensions = {}
        self.num_dimensions = -1

        self.optimize = kwargs.get('optimize', False)
        self.tile_size = kwargs.get('tile_size', 128)
        self.tile_overlap = kwargs.get('tile_overlap', 0)
        self.tile_format = kwargs.get('tile_format', "png")
        self.image_quality = kwargs.get('image_quality', 1.0)
        self.resize_filter = kwargs.get('resize_filter', "bicubic")

    @property
    def file_size(self):
        return os.path.getsize(self.file_path)

    @property
    def view_size(self):
        return os.path.getsize(self.view_path)

    def set_img_dimensions(self):
        """Create and assign properties for dimension objects"""

        assert len(self.img_data_shape) <= 3
        if len(self.img_data_shape) == 2:
            dim_assignment = ['X', 'Y']
        else:
            dim_assignment = ['X', 'Y', 'C']

        self.num_dimensions = len(dim_assignment)
        self.img_dimensions['isColorImage'] = True
        self.img_dimensions['dimensions'] = {}

        for dim in range(len(self.img_data_shape)):
            self.img_dimensions['dimensions'][dim] = {}
            self.img_dimensions['dimensions'][dim]["assignment"] = dim_assignment[dim]
            self.img_dimensions['dimensions'][dim]["length"] = self.img_data_shape[dim]
            self.img_dimensions['dimensions'][dim]["resolution"] = ""
            self.img_dimensions['dimensions'][dim]["units"] = ""

    def get_view_asset_dict(self, storage_bucket, upload_key):
        upload_key = upload_key.rstrip('/')
        json_dict = {
            "bucket": storage_bucket,
            "key": upload_key,
            "type": "View",
            "size": self.file_size,
            "fileType": "Image"
        }
        return json_dict

    def load_image(self, standard_image_file_path, subimgrow_subimgcol=(-1, -1), nsubimgrow_nsubimgcol=(-1, -1)):
        # Set file path
        self.file_path = standard_image_file_path
        self.file_format = os.path.splitext(self.file_path)[1]

        # Load Image
        print 'Reading entire image ...'
        image = PIL.Image.open(self.file_path)
        image = image.convert("RGB")
        print 'Done reading entire image ...'

        # Get image dimensions
        self.img_data_shape = image.size

        # Save to local storage output deepzoom files
        if subimgrow_subimgcol != (-1, -1):  # Parallelized
            # Define sub-region parameters to limit tile asset generation
            sub_img_row = subimgrow_subimgcol[0]
            sub_img_col = subimgrow_subimgcol[1]
            n_sub_img_rows = nsubimgrow_nsubimgcol[0]
            n_sub_img_cols = nsubimgrow_nsubimgcol[1]

            # Check to see if processor should process entire image view instead of just a sub-region
            if n_sub_img_rows == -1 or n_sub_img_cols == -1 \
                    or sub_img_col == -1 or sub_img_row == -1:
                raise NotImplementedError
            else:
                destination = os.path.join('view', 'slide.dzi')

                # Initialize DeepZoomGenerator from OpenSlide Python API
                width, height = image.size

                image_creator = ImageCreator(tile_size=self.tile_size, tile_overlap=self.tile_overlap,
                                             tile_format=self.tile_format, image_quality=self.image_quality)
                image_creator.image = image
                image_creator.descriptor = DeepZoomImageDescriptor(width=width,
                                                          height=height,
                                                          tile_size=self.tile_size,
                                                          tile_overlap=self.tile_overlap,
                                                          tile_format=self.tile_format)
                # Create tiles
                image_files = _get_or_create_path(_get_files_path(destination))
                for level in xrange(image_creator.descriptor.num_levels):
                    level_dir = _get_or_create_path(os.path.join(image_files, str(level)))
                    level_image = image_creator.get_image(level)

                    # Determine number of rows and columns of tiles at this level
                    num_columns, num_rows = image_creator.descriptor.get_num_tiles(level)

                    # Iterate over all tiles to determine which ones fall in svs-processor sub-region
                    for column in xrange(num_columns):
                        for row in xrange(num_rows):
                            # Calculate the appropriate sub-region column and row index for this tile
                            try:
                                tile_sub_img_col = int(column / (float(num_columns) / n_sub_img_cols))
                            except ZeroDivisionError:
                                tile_sub_img_col = 0
                            try:
                                tile_sub_img_row = int(row / (float(num_rows) / n_sub_img_rows))
                            except ZeroDivisionError:
                                tile_sub_img_row = 0

                            # Check if this tile falls in the given sub-region
                            if tile_sub_img_col == sub_img_col and \
                                    tile_sub_img_row == sub_img_row:
                                bounds = image_creator.descriptor.get_tile_bounds(level, column, row)
                                tile = level_image.crop(bounds)
                                format = image_creator.descriptor.tile_format
                                tile_path = os.path.join(level_dir,
                                                         '%s_%s.%s' % (column, row, format))
                                tile_file = open(tile_path, 'wb')
                                if image_creator.descriptor.tile_format == 'jpg':
                                    jpeg_quality = int(self.image_quality * 100)
                                    tile.save(tile_file, 'JPEG', quality=jpeg_quality)
                                else:
                                    tile.save(tile_file)
                # Create descriptor
                image_creator.descriptor.save(destination)

            # Set image dimensions properties
            self.set_img_dimensions()
        else:
            # No need to save any view assets
            self.view_format = self.file_format

    def _save_view(self, image, exploded_format='dzi'):
        """ Save exploded assets from the image in internal storage format to output local path.
        These files will be uploaded to S3"""

        # Make view directory
        if not os.path.exists('view'):
            os.makedirs('view')

        # Save asset in appropriate format
        filename = os.path.join(
            'view',
            # Assumed that ingested file will have .nii.gz or .nii as extensions
            os.path.basename('slide.dzi')
        )
        utils.save_asset(
            image,
            exploded_format,
            filename,
            optimize=self.optimize, tile_size=self.tile_size,
            tile_overlap=self.tile_overlap, tile_format=self.tile_format,
            image_quality=self.image_quality, resize_filter=self.resize_filter
        )
        # Save thumbnail
        if exploded_format == 'dzi':
            timage = image.copy()
            timage.thumbnail((200, 200), PIL.Image.ANTIALIAS)
            timage.save(filename.replace('.dzi', '_thumbnail.png'))

        self.view_path = self.file_path  # Setting to original source file
        return


class StandardImageProcessor(BaseImageProcessor):
    required_inputs = ['file']

    def __init__(self, *args, **kwargs):
        super(StandardImageProcessor, self).__init__(*args, **kwargs)
        self.file = self.inputs.get('file')
        self.session = boto3.session.Session()
        self.s3_client = self.session.client('s3', config=Config(signature_version='s3v4'))
        self.upload_key = None
        try:
            self.optimize = utils.str2bool(self.inputs.get('optimize_view'))
        except AttributeError:
            self.optimize = False

        try:
            self.tile_size = int(self.inputs.get('tile_size'))
        except (ValueError, KeyError, TypeError) as e:
            self.tile_size = 128

        try:
            self.tile_overlap = int(self.inputs.get('tile_overlap'))
        except (ValueError, KeyError, TypeError) as e:
            self.tile_overlap = 0

        try:
            self.tile_format = self.inputs.get('tile_format')
            if self.tile_format is None:
                self.tile_format = "png"
        except KeyError:
            self.tile_format = "png"

        try:
            self.image_quality = float(self.inputs.get('image_quality'))
        except (ValueError, KeyError, TypeError) as e:
            self.image_quality = 1.0

        try:
            self.resize_filter = self.inputs.get('resize_filter')
        except KeyError:
            self.resize_filter = "bicubic"

    def load_and_save(self, subimgrow_subimgcol=(-1, -1), nsubimgrow_nsubimgcol=(-1, -1)):
        if os.path.isfile(self.file):
            output_file = StandardImageOutputFile(optimize=self.optimize, tile_size=self.tile_size,
                                                  tile_overlap=self.tile_overlap, tile_format=self.tile_format,
                                                  image_quality=self.image_quality, resize_filter=self.resize_filter)
            if self.file.endswith('.jp2') or self.file.endswith('.jpx'):
                os.system('opj_decompress -quiet -i %s -o output.png > tmp.log' % self.file)
                output_file.file_path = 'output.png'
                self.outputs.append(output_file)
            else:
                output_file.load_image(self.file, subimgrow_subimgcol, nsubimgrow_nsubimgcol)
                self.outputs.append(output_file)

    def task(self):
        # self._load_image()
        self.LOGGER.info('Got inputs {}'.format(self.inputs))

        # Get sub_region index
        try:
            sub_region = self.inputs['sub_region_file']
            col = int(re.match(re.compile(r'([0-9]+)_([0-9]+).txt'), sub_region).groups()[0])
            row = int(re.match(re.compile(r'([0-9]+)_([0-9]+).txt'), sub_region).groups()[1])
            sub_region_text = open(sub_region, 'r').read().replace('\n', '').replace('\r', '')
            n_col = int(re.match(re.compile(r'([0-9]+),([0-9]+)'), sub_region_text).groups()[0])
            n_row = int(re.match(re.compile(r'([0-9]+),([0-9]+)'), sub_region_text).groups()[1])
        except KeyError:
            row = -1
            col = -1
            n_row = -1
            n_col = -1
        except IndexError:
            # Process whole file; for some reason, sub_region file incorrectly named
            row = -1
            col = -1
            n_row = -1
            n_col = -1

        # Load and save view images
        self.load_and_save(subimgrow_subimgcol=(row, col), nsubimgrow_nsubimgcol=(n_row, n_col))

        if os.path.isfile(self.file):
            # Output file is just the one and only file in outputs
            output_file = self.outputs[0]

            # Check if this is deep-zoom generator task
            if os.path.isfile('view/slide.dzi'):
                # Create view asset pointing to slide.dzi
                self.upload_key = os.path.join(
                    self.settings.storage_directory,
                    'view'
                )
                if row == 0 and col == 0:
                    with open('view_asset_info.json', 'w') as fp:
                        json.dump(output_file.get_view_asset_dict(
                            self.settings.storage_bucket,
                            self.upload_key
                        ), fp)

                # Write dimensions API response
                with open('view/dimensions.json', 'w') as fp:
                    json.dump(output_file.img_dimensions, fp)

            # Make sure not a process running for deep-zoom generator but a standard Image instead
            elif (n_row, n_col) == (-1, -1):
                # Create view asset pointing to source file
                # Create create-asset JSON object file called view_asset_info.json
                self.upload_key = os.path.join(
                    self.settings.storage_directory,
                    os.path.basename(self.outputs[0].file_path)
                )
                with open('view_asset_info.json', 'w') as fp:
                    json.dump(self.outputs[0].get_view_asset_dict(
                        self.settings.storage_bucket,
                        self.upload_key
                    ),
                        fp)

            # Generate properties metadata.json metadata
            if row < 1 and col < 1:
                metadata = []
                img_dimensions = output_file.img_dimensions
                for dim in range(output_file.num_dimensions):
                    for property_key_suffix in ["assignment", "length", "resolution", "units"]:
                        # Initialize property
                        property = {}

                        # Set property key and value
                        property_key = 'dimensions.%i.%s' % (dim, property_key_suffix)
                        property_value = str(img_dimensions['dimensions'][dim][property_key_suffix])

                        # Create property instance
                        property["key"] = property_key
                        property["value"] = property_value
                        property["dataType"] = "String"
                        property["category"] = "Blackfynn"
                        property["fixed"] = False
                        property["hidden"] = False
                        metadata.append(property)
                with open('metadata.json', 'w') as fp:
                    json.dump(metadata, fp)

            # Upload output file to s3
            self.upload_key = os.path.join(
                self.settings.storage_directory,
                os.path.basename(output_file.file_path)
            )
            self._upload(output_file.file_path, self.upload_key)
