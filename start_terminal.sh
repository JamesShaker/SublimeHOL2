DIRECTORY=$1
FILTERPATH=$2
HOLPATH=$3
stty -echo; cd "$DIRECTORY";
(
echo 'current_backend := PPBackEnd.vt100_terminal;' ;
"$FILTERPATH"
) | "$HOLPATH"
