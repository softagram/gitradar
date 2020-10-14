# gitradar


# Usage

How to run:

```
./gitradar.sh ../../your-repo-dir
```

![Demo gif](https://github.com/softagram/gitradar/blob/master/gitradar.gif)


# Install

Go to panwid/ and run   `python3 setup.py install`


## Advanced config

If wanting to enrich columns with env names, e.g. 2.0.0 *instance1*,
instead of plain versions, please customize env mapping:

```
    cp src/customizedenvs.py{.template,}
```

And then modify that customizedenvs.py to do your mapping.

