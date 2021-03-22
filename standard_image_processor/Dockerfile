# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# TEST IMAGE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FROM pennsieve/base-processor-pandas-test:1-5800e81 as test

RUN apk add --no-cache --update build-base \
        gcc \
        autoconf \
        automake \
        libtool \
        zlib-dev \
        libxml2-dev \
        libffi-dev \
        jpeg-dev \
        openjpeg-dev \
        openjpeg-tools \
        tiff-dev \
        glib-dev \
        gdk-pixbuf-dev \
        sqlite-dev \
        libjpeg-turbo-dev \
        libexif-dev \
        lcms2-dev \
        fftw-dev \
        giflib-dev \
        libpng-dev \
        musl-dev \
        libwebp-dev \
        orc-dev \
        poppler-dev \
        librsvg-dev \
        libgsf-dev \
        openexr-dev \
        gtk-doc

RUN pip install --no-cache-dir moto pylint pytest pytest-cov

# install requirements
RUN pip install --upgrade pip
RUN pip install --no-cache-dir botocore==1.17.63 \
                               awscli==1.12.0 \
                               pillow


RUN wget -O- https://github.com/jcupitt/libvips/releases/download/v8.6.3/vips-8.6.3.tar.gz | tar xzC /tmp
RUN cd /tmp/vips-8.6.3 \
        && ./configure --prefix=/usr --disable-static --disable-debug \
        && make V=0 \
        && make install

# code: processor
COPY standard_image_processor/standard_image_processor    /app/standard_image_processor
COPY standard_image_processor/run.py                      /app/run.py

# code: tests
COPY standard_image_processor/tests                       /app/tests

WORKDIR /app

ENTRYPOINT [""]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# PRODUCTION IMAGE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FROM pennsieve/base-processor-pandas:1-5800e81 as prod

RUN apk add --no-cache --update build-base \
        gcc \
        autoconf \
        automake \
        libtool \
        zlib-dev \
        libxml2-dev \
        libffi-dev \
        jpeg-dev \
        openjpeg-dev \
        openjpeg-tools \
        tiff-dev \
        glib-dev \
        gdk-pixbuf-dev \
        sqlite-dev \
        libjpeg-turbo-dev \
        libexif-dev \
        lcms2-dev \
        fftw-dev \
        giflib-dev \
        libpng-dev \
        musl-dev \
        libwebp-dev \
        orc-dev \
        poppler-dev \
        librsvg-dev \
        libgsf-dev \
        openexr-dev \
        openssl-dev \
        gtk-doc

RUN pip install --no-cache-dir moto pylint pytest pytest-cov

# install requirements
RUN pip install --upgrade pip
RUN pip install --no-cache-dir botocore==1.17.63 \
                               awscli==1.13.0 \
                               pillow

RUN wget -O- https://github.com/jcupitt/libvips/releases/download/v8.6.3/vips-8.6.3.tar.gz | tar xzC /tmp
RUN cd /tmp/vips-8.6.3 \
        && ./configure --prefix=/usr --disable-static --disable-debug \
        && make V=0 \
        && make install

# code: processor
COPY standard_image_processor/standard_image_processor    /app/standard_image_processor
COPY standard_image_processor/run.py                      /app/run.py

# code: tests
COPY standard_image_processor/tests                       /app/tests

WORKDIR /app

ENTRYPOINT [""]
