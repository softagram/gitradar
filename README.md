# gitradar


# Usage

```
./gitradar.sh path-to-your-git-repo
```

![Demo gif](https://github.com/softagram/gitradar/blob/master/gitradar.gif)


# Install

Go to panwid/ and run   `python3 setup.py install`

venv can be used to avoid install all the dependencies into global Python space. gitradar.sh is a helper which launches it using python from venv. There is a requirements.txt for getting couple of packages installed.



## Advanced config

If wanting to enrich columns with env names, e.g. 2.0.0 *instance1*,
instead of plain versions, please customize env mapping:

```
    cp src/customizedenvs.py{.template,}
```

And then modify that customizedenvs.py to do your mapping.

## Contribute

Documentation, flexibility, etc. needs to be improved.

