func() {
    echo hello
    echo MARKER
    echo -- $@
    var1=$1
    var2=$2
    return 2
}
