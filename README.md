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
```

All static assets such as css and png files are to be in the `static/` 
directory. Any url prefixed with `/static/` will directly serve these files.

## Future changes

Both the markuphive.com service and this SDK are in beta, which means the 
service infrastructure and SDK can change before becoming production ready 
and stable.
