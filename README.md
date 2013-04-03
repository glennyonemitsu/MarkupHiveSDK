# Markup Hive SDK

This is an SDK for the markuphive.com hosting platform. This tool is 
intended for developing web applications for that service.

The host template language is Jade with a couple of feature extensions.
Jade can help people be incredibly productive, but the cost to learn how 
to implement it correctly for a site is a real hurdle to many who do not 
use it regularly. As a result people do not give Jade a chance because a 
"Hello, World!" example takes longer than the 30 seconds it would take in 
their native environment.

If you are new to Jade there is also a site dedicated to helping you 
[learn the features and syntax of Jade](http://www.learnjade.com).
 
## Basic usage

```
# help output
$ markuphive --help
$ markuphive create --path test_project
# do some coding
$ markuphive run_server --path test_project
```

## Project files
In directory test_project you will have the following directories:

- test_project/data
- test_project/templates
- test_project/static
- test_project/static/css
- test_project/static/img
- test_project/static/js

And the file:

- test_project/app.yaml

If you run `markuphive create` with the `--bootstrap` flag, your static 
directory will have all the files from the Twitter Bootstrap framework 
included. The `templates/base.jade` file has some skeleton code to include 
what you need to get started.

### app.yaml 
`app.yaml` contains commented out code. In a nutshell you specify the route 
rule and the jade file associated with that rule. The following are a few 
rules you can use:

```
/
/about/
/members/<member_name>/
```

In that last route the variable `member_name` will be available in your 
jade file.

Each route can have one or more data files. These are static text files in 
the `data/` directory that are either json or yaml format. The `data/ `
directory does not need to be specified. Each succeeding data file with 
matching keys will overwrite keys in the preceeding file. 

#### 404 handling

You can also specify a rule as `404`. As you might expect, this will make 
all requests that do not match a normal route rule to be served by that 
special 404 route rule. Your 404 handler is also specified with a template 
and any other data files you want to associate with it.

Due to technical limitations, variables from route rules such as 
`member_name` above will be overwritten by any data files with the same 
key.

In the `data/` directory just create files with a .json or .yaml extension 
and the SDK will properly load in the correct format. Due to json's strict 
formatting rules it is suggested to use the yaml format when possible.

Some completed routes are shown below:

```
routes:
  - rule: /
    template: home.jade
  - rule: /about-us/
    template: about-us.jade
    data: team.yaml
  - rule: /portfolio/
    template: portfolio.jade
    data: [projects.json, clients.yaml]
  - rule: 404
    template: not-found.jade
```

### Static assets (images, css, javascript)

All static assets such as css and png files are to be in the `static/` 
directory. Any url prefixed with `/static/` will directly serve these files.

#### SCSS "Sassy CSS"

SCSS is a superset of CSS3 that the SDK and hosting platform will 
automatically convert back into native css. Simply add any file with the 
`.scss` file extension in the `static/css/` folder. In your templates you 
simply reference the `.scss` filename directly. You do not need to 
"translate" the filename to a `.css` extension.

For example, if your scss file is in `static/css/style.scss` you can use 
the link tag as 
`link(rel='stylesheet', media='screen', href='/static/css/style.scss')`

Currently the `@import` directive is not supported.

SASS is the older version of a css preprocessor syntax, not to be confused 
with SCSS. Currently SASS is not supported.

[Learn more about the SCSS syntax at sass-lang.com](http://sass-lang.com/).

#### Coffeescript files

[Coffeescript](http://coffeescript.org/) is a neat and well organized 
language that compiles into properly linting javascript code. The SDK and 
hosting platform automatically converts `.coffeescript` files placed 
inside the `static/js/` directory. Like with scss, you also reference the 
file with the `.coffeescript` extension like so:

```
script(src='/static/js/my-script.coffeescript')
```

#### Favicons

Favicon files are also supported. Simply place the favicon.ico file in the 
`static/` directory. Requests for `example.com/favicon.ico` will look into 
this directory for the file, even though `/static/` is not in the url.

## Future changes

Both the markuphive.com service and this SDK are in beta, which means the 
service infrastructure and SDK can change before becoming production ready 
and stable.
