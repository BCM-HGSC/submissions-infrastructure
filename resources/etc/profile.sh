# TODO: render

for i in {profile_dir}/*.sh ; do
    if [ -r "$i" ]; then
        . "$i"
    fi
done
